from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import time
import numpy as np
import os.path as osp

from sklearn.preprocessing import normalize as sklearn_normalize
from sklearn.svm import LinearSVC
import torch
import logging
from torchvision import transforms

from src import voting_cython, utils, genericdataset


def query_feature(featureExtractor, query_data, prop_data, dataset, cfg_voting, cfg):

    """ Extract query features """

    # - dataloader
    normalize = transforms.Normalize(
        mean=cfg.RET.NETWORK.PIXELMEAN,
        std=cfg.RET.NETWORK.PIXELSTD
    )
    transform = transforms.Compose([
        transforms.ToTensor(),
        normalize
    ])
    loader_qu = torch.utils.data.DataLoader(
        genericdataset.ImagesStylizationsQueriesFromList(query_data, query_data['img_ids'], dataset, cfg,
                                                         prop_data_2=prop_data, rois_file=dataset['anno_file_qu'],
                                                         scales=cfg.RET.IMG.SCALES, transform=transform,
                                                         f_stride=featureExtractor.feature_map_stride),
        batch_size=1, shuffle=False, num_workers=1, pin_memory=True
    )

    num_images_qu = len(loader_qu)
    feat_qu_list = []
    feat_v_list = []
    shift_v_list = []
    tfq_1 = time.time()
    num_votes_qu = [0]

    # - initialize info_vec_qu
    info_vec_qu_count = 0
    info_vec_qu = np.zeros([10000, 8], dtype=np.int32)  # zeros -> label default

    t_overall_query = time.time()
    for i, (images, images_aug, imgids, imsizes, queries, prop) in enumerate(loader_qu):
        if queries['rois'].size()[1] == 0:
            logging.info('No rois --> continue ...')
            continue
        with torch.no_grad():
            if cfg.RET.CUDA:
                images = [img.cuda() for img in images]
                for ii in range(len(images_aug)):
                    images_aug[ii] = [img.cuda() for img in images_aug[ii]]
                imsizes = [imsize.cuda() for imsize in imsizes]
                prop['rois'] = prop['rois'].cuda()
                prop['rois'] = prop['rois'].cuda()
                queries['rois'] = queries['rois'].cuda()
                imsizes = [imsize.cuda() for imsize in imsizes]
            # - query feature extraction
            rois_out, rois_out_rel, feat, _ = featureExtractor(images, images_aug, imsizes, queries, cfg.RET.IMG.SCALES)

            # - local patch feature extraction
            if cfg_voting.FLAG != 0:
                for ii, (qu, qu_rel) in enumerate(zip(queries['rois'][0], queries['rois_rel'][0])):
                    prop_tmp = prop.copy()
                    # - remove proposals with too few overlap
                    thresh_inter = cfg_voting.INTERTHRESH
                    idx_ov = utils.bbs_inter_torch(qu, prop_tmp['rois'][0]) > thresh_inter
                    for key in prop_tmp.keys():
                        if prop_tmp[key].ndim == 3:
                            prop_tmp[key] = prop_tmp[key][:, idx_ov, :]
                        else:
                            prop_tmp[key] = prop_tmp[key][:, idx_ov]
                    # - remove proposals with too few iou
                    thresh_iou = cfg_voting.IOUTHRESH
                    iou_prop = utils.bbs_iou_torch(qu, prop_tmp['rois'][0])
                    idx_ov = iou_prop > thresh_iou
                    for key in prop_tmp.keys():
                        if prop_tmp[key].ndim == 3:
                            prop_tmp[key] = prop_tmp[key][:, idx_ov, :]
                        else:
                            prop_tmp[key] = prop_tmp[key][:, idx_ov]

                    if torch.sum(idx_ov).cpu().numpy() != 0:
                        # - local patch feature extraction
                        rois_v, rois_rel_v, feat_v, activation_v = featureExtractor(images,
                                                                                    images_aug,
                                                                                    imsizes,
                                                                                    prop_tmp,
                                                                                    cfg.RET.IMG.SCALES,
                                                                                    get_activation=True)
                        # - nms based on feature activation
                        dets = rois_v
                        dets[:, 0] = activation_v
                        dets = dets[:, torch.LongTensor([1, 2, 3, 4, 0])]
                        nms_thresh = 0.1
                        while 1:
                            idx_keep = utils.nms_torch(dets, nms_thresh)
                            if len(idx_keep) >= min(cfg_voting.NUMVOTES, dets.shape[0]):
                                break
                            else:
                                nms_thresh += 0.1
                        idx_keep = idx_keep[0:cfg_voting.NUMVOTES]
                        num_votes_qu.append(len(idx_keep))
                        rois_v, rois_rel_v, feat_v = rois_v[idx_keep, :], rois_rel_v[idx_keep, :], feat_v[idx_keep, :]
                        feat_v_np = feat_v.cpu().numpy().copy()
                        feat_v_list.append(list(feat_v_np))
                        del feat_v, feat_v_np
                        # - compute voting vectors
                        shift_v_tmp = utils.get_shift_vec(qu, rois_v[:, 1:]).cpu().numpy()
                        shift_v_list.append(shift_v_tmp)
                    else:
                        # - no suitable patches found
                        num_votes_qu.append(0)

            # - convert back to cpu
            rois_rel_np = rois_out_rel.cpu().numpy().copy()
            rois_np = rois_out.cpu().numpy().copy()
            feat_np = feat.cpu().numpy().copy()
            labels = [list(l[0].cpu().numpy().reshape(-1)) for l in queries['labels']]
            quids = [list(l[0].cpu().numpy().reshape(-1)) for l in queries['quids']]
            assert(rois_np.shape[0] == len(labels))
            del rois_out, rois_out_rel, feat
        # - add to list for retrieval
        feat_qu_list.append(list(feat_np))
        del feat_np

        # - add to info_vec
        for jj in range(rois_rel_np.shape[0]):
            # - [img_id, x1, y1, x2, y2, scale, quid, label]
            info_vec_qu[info_vec_qu_count, 0] = np.array(quids[jj]).reshape(1, -1)
            info_vec_qu[info_vec_qu_count, 1] = imgids[0][jj].numpy()
            info_vec_qu[info_vec_qu_count, 2:6] = (rois_rel_np[jj, 1:5].reshape(1, -1) *
                                                   cfg.RET.INFOVEC.BBSSCALE).astype(np.uint32)
            info_vec_qu[info_vec_qu_count, 6] = 1
            if np.array(labels[jj]).shape[0] > 0:
                info_vec_qu[info_vec_qu_count, 7] = np.array(labels[jj]).reshape(1, -1)
            info_vec_qu_count += 1

        if ((i+1) % 10) == 0:
            logging.info(f'num votes: {num_votes_qu}')
            logging.info('Extract queries: %d/%d %3.2f sec' % (i+1, num_images_qu, time.time() - tfq_1))

    # - remove empty rows
    info_vec_qu = info_vec_qu[0:info_vec_qu_count, :]
    features_qu = np.concatenate(feat_qu_list, axis=0)
    del feat_qu_list

    if (cfg_voting.FLAG != 0) and feat_v_list:
        features_v = np.concatenate(feat_v_list, axis=0)
        shift_v = np.concatenate(shift_v_list, axis=0)
    else:
        features_v = np.array([])
        shift_v = np.array([])
    del feat_v_list, shift_v_list

    # - re-order wrt quids
    idx_sort = np.argsort(info_vec_qu[:, 0])
    info_vec_qu = info_vec_qu[idx_sort, :]
    features_qu = features_qu[idx_sort, :]
    # - re-order voting features
    if features_v.shape[0] > 0:
        num_votes_qu_tmp = [0]
        features_v_tmp = []
        shift_v_tmp = []
        for qid in idx_sort:
            rs, re = sum(num_votes_qu[0:qid+1]), sum(num_votes_qu[0:qid+2])
            features_v_tmp.append(features_v[rs:re, :])
            shift_v_tmp.append(shift_v[rs:re, :])
            num_votes_qu_tmp.append(features_v[rs:re, :].shape[0])
        features_v = np.concatenate(features_v_tmp, axis=0)
        shift_v = np.concatenate(shift_v_tmp, axis=0)
        num_votes_qu = num_votes_qu_tmp
    logging.info('Extracting queries took %d: %3.2f sec', i, (time.time() - tfq_1))

    return features_qu, info_vec_qu, num_votes_qu, features_v, shift_v, t_overall_query


def retrieval_voting(index,
                     info_vec,
                     info_vec_imgrange,
                     pqRecon,
                     pqReconhdf5,
                     features_qu,
                     info_vec_qu,
                     num_votes_qu,
                     features_v,
                     shift_v,
                     dataset,
                     cfg):

    """ Retrieval based on iterative voting """

    retrievals = {}

    tfaiss_1 = time.time()
    retrieval_time = []
    num_qu = features_qu.shape[0]
    tt1 = time.time()

    # knn search
    nn_dist, nn_idx = index.search(features_qu.astype('float32').copy(), cfg.RET.FAISS.NUM_KNN)
    nn_dist = utils.normalize_dist(nn_dist)

    # - compute shift vector for nn proposal in query image
    shift_qu = np.zeros([nn_idx.shape[0], 3])
    for qi in range(nn_idx.shape[0]):
        img_id = info_vec_qu[qi][1]
        img_size = dataset['imagesizes'][img_id] / np.max(dataset['imagesizes'][img_id])
        bbs_qu_rel = info_vec_qu[qi][2:6] / cfg.RET.INFOVEC.BBSSCALE
        bbs_qu = bbs_qu_rel * [img_size[1], img_size[0], img_size[1], img_size[0]]
        idx_tmp = np.where(info_vec[nn_idx[qi, :], 1] == img_id)[0]
        if idx_tmp.shape[0] != 0:
            # - hit in originating image
            bbs_ret_rel = info_vec[nn_idx[qi, idx_tmp[0]], 2:6].reshape(1, -1) / cfg.RET.INFOVEC.BBSSCALE
            bbs_ret = bbs_ret_rel * [img_size[1], img_size[0], img_size[1], img_size[0]]
        else:
            # - not hit in originating image
            bbs_ret = bbs_qu
        shift_qu[qi, :] = utils.get_shift_vec(torch.Tensor(bbs_qu), torch.Tensor(bbs_ret.reshape(1, -1))).cpu().numpy()

    # - convert results to retrieval vec
    retrievals_tmp = utils.get_retrievals(nn_idx, nn_dist, info_vec, info_vec_qu[:, 0], cfg)
    retrieval_time.append((time.time()-tt1)/num_qu)

    if cfg.RET.VOTING.FLAG:
        # Local patch descriptor voting
        if features_v.shape[0] != 0:
            tt1 = time.time()
            nn_dist_v, nn_idx_v = index.search(features_v.astype('float32').copy(), cfg.RET.FAISS.NUM_KNN)
            nn_dist_v = utils.normalize_dist(nn_dist_v)
        else:
            nn_idx_v = np.array([]).reshape(0, 2)
            nn_dist_v = np.array([]).reshape(0, 2)
            shift_v = np.array([]).reshape(0, 2)

        nn_idx, nn_dist, nn_idx_v, nn_dist_v, retrievals_tmp = voting_cython.vote(nn_idx,
                                                                                  nn_dist,
                                                                                  info_vec,
                                                                                  info_vec_imgrange,
                                                                                  info_vec_qu,
                                                                                  nn_idx_v,
                                                                                  nn_dist_v,
                                                                                  shift_v,
                                                                                  shift_qu,
                                                                                  num_votes_qu,
                                                                                  dataset,
                                                                                  cfg)
        retrieval_time.append((time.time()-tt1)/num_qu)

    # save retrievlas
    retrievals['_0'] = retrievals_tmp
    logging.info('Faiss retrieval took: %3.2f sec' % (time.time()-tfaiss_1))

    # ----------------------------------------------------------------------
    # QUREY EXPANSION using NN
    # ----------------------------------------------------------------------
    if cfg.RET.LQUEXP.TYPE == 'nn':

        tt1 = time.time()
        # - filter nn_idx
        nn_idx_qe, nn_dist_qe = utils.filter_singlehit_perimage(nn_idx, nn_dist, info_vec)

        # - filter nn_idx_v
        if cfg.RET.VOTING.FLAG:
            nn_idx_v_qe, nn_dist_v_qe = utils.filter_singlehit_perimage(nn_idx_v, nn_dist_v, info_vec)

        # - several rounds of query expansion
        for r in range(len(cfg.RET.LQUEXP.NUM)):
            if cfg.RET.LQUEXP.NUM[r] == 0:
                continue
            tqe1 = time.time()
            logging.info('-- Query expansion round: %d' % r)
            # - get all features
            features_qu_qe = np.zeros_like(features_qu)
            for qid in range(nn_idx_qe.shape[0]):
                nn_idx_tmp = nn_idx_qe[qid, :].copy()  # changes over query expansion rounds
                nn_idx_tmp = nn_idx_tmp[0:cfg.RET.LQUEXP.NUM[r]].copy()
                nn_idx_tmp = nn_idx_tmp[nn_idx_tmp != -1]
                f_qu = features_qu[qid, :].reshape(1, -1)  # original query
                # - reconstruct feature of retrieved regions
                f_nn = pqRecon.pq.decode(pqReconhdf5['features'][np.sort(nn_idx_tmp), :])
                f = np.concatenate((f_qu, f_nn), axis=0)
                features_qu_qe[qid, :] = sklearn_normalize(np.mean(f, axis=0).reshape(1, -1), axis=1, norm='l2')

                if cfg.RET.VOTING.FLAG:
                    if features_v.shape[0] != 0:
                        idx_range = list(range(np.sum(num_votes_qu[0:(qid+1)]), np.sum(num_votes_qu[0:(qid+2)])))
                        f_v = features_v[idx_range, :]
                        nn_idx_v_tmp = nn_idx_v_qe[idx_range, 0:cfg.RET.LQUEXP.NUM[r]]
                        for vid, f_v_qu in enumerate(f_v):
                            nn_idx_v_tmp_tmp = nn_idx_v_tmp[vid, :].copy()
                            nn_idx_v_tmp_tmp = nn_idx_v_tmp_tmp[nn_idx_v_tmp_tmp != -1]
                            f_v_nn = pqRecon.pq.decode(pqReconhdf5['features'][np.sort(nn_idx_v_tmp_tmp), :])
                            f = np.concatenate([f_v_qu.reshape(1, -1), f_v_nn], axis=0)
                            features_v[idx_range[vid], :] = sklearn_normalize(np.mean(f, axis=0).reshape(1, -1),
                                                                              axis=1, norm='l2')
            # - knn search
            nn_dist_qe, nn_idx_qe = index.search(features_qu_qe.astype('float32'), cfg.RET.FAISS.NUM_KNN)
            nn_dist_qe = utils.normalize_dist(nn_dist_qe)

            # - update shift_qu
            shift_qu_qe = np.zeros([nn_idx_qe.shape[0], 3])
            for qi in range(nn_idx_qe.shape[0]):
                img_id = info_vec_qu[qi][1]
                img_size = dataset['imagesizes'][img_id] / np.max(dataset['imagesizes'][img_id])
                bbs_qu_rel = info_vec_qu[qi][2:6] / cfg.RET.INFOVEC.BBSSCALE
                bbs_qu = bbs_qu_rel * [img_size[1], img_size[0], img_size[1], img_size[0]]
                idx_tmp = np.where(info_vec[nn_idx_qe[qi, :], 1] == img_id)[0]
                if idx_tmp.shape[0] != 0:
                    # - hit in originating image -> update
                    bbs_ret_rel = info_vec[nn_idx_qe[qi, idx_tmp[0]], 2:6].reshape(1, -1) / cfg.RET.INFOVEC.BBSSCALE
                    bbs_ret = bbs_ret_rel * [img_size[1], img_size[0], img_size[1], img_size[0]]
                    shift_qu_qe[qi, :] = utils.get_shift_vec(torch.Tensor(bbs_qu),
                                                             torch.Tensor(bbs_ret.reshape(1, -1))).cpu().numpy()

            if cfg.RET.VOTING.FLAG:
                # Local patch descriptor voting
                if features_v.shape[0] != 0:
                    # - knn search
                    nn_dist_v_qe, nn_idx_v_qe = index.search(features_v.astype('float32').copy(), cfg.RET.FAISS.NUM_KNN)
                    nn_dist_v_qe = utils.normalize_dist(nn_dist_v_qe)
                    # - update shift_v -> shift_v_qe
                    shift_v_qe = np.zeros([nn_idx_v.shape[0], 3])
                    for qi in range(info_vec_qu.shape[0]):
                        img_id = info_vec_qu[qi][1]
                        idx_range = list(range(np.sum(num_votes_qu[0:(qi+1)]), np.sum(num_votes_qu[0:(qi+2)])))
                        bbs_qu_rel = info_vec_qu[qi][2:6] / cfg.RET.INFOVEC.BBSSCALE
                        img_size = dataset['imagesizes'][img_id] / np.max(dataset['imagesizes'][img_id])
                        bbs_qu = bbs_qu_rel * [img_size[1], img_size[0], img_size[1], img_size[0]]
                        for ii in idx_range:
                            idx_tmp = np.where(info_vec[nn_idx_v_qe[ii, :], 1] == img_id)[0]
                            if idx_tmp.shape[0] != 0:
                                # - hit in originating image
                                bbs_ret_rel = info_vec[nn_idx_v_qe[ii, idx_tmp[0]], 2:6].reshape(1, -1) \
                                              / cfg.RET.INFOVEC.BBSSCALE
                                bbs_ret = bbs_ret_rel * [img_size[1], img_size[0], img_size[1], img_size[0]]
                                shift_v_qe[ii, :] = utils.get_shift_vec(torch.Tensor(bbs_qu),
                                                                        torch.Tensor(bbs_ret.reshape(1, -1))).cpu().numpy()
                            else:
                                shift_v_qe[ii, :] = shift_v[ii, :]

                else:
                    nn_idx_v_qe = np.array([]).reshape(0, 2)
                    nn_dist_v_qe = np.array([]).reshape(0, 2)
                    shift_v_qe = np.array([]).reshape(0, 2)

                (nn_idx_qe,
                 nn_dist_qe,
                 nn_idx_v_qe,
                 nn_dist_v_qe,
                 retrievals_qe_tmp) = voting_cython.vote(nn_idx_qe,
                                                         nn_dist_qe,
                                                         info_vec,
                                                         info_vec_imgrange,
                                                         info_vec_qu,
                                                         nn_idx_v_qe,
                                                         nn_dist_v_qe,
                                                         shift_v_qe,
                                                         shift_qu_qe,
                                                         num_votes_qu,
                                                         dataset,
                                                         cfg,
                                                         vote_name=('_qe_%d' % r))
            else:
                # - convert results to retrieval vec
                retrievals_qe_tmp = utils.get_retrievals(nn_idx_qe, nn_dist_qe, info_vec, cfg)

            retrievals['_qe_%d' % r] = retrievals_qe_tmp
            logging.info('-- Query expansion round %d took %3.2f' % (r, time.time() - tqe1))

        retrieval_time.append((time.time()-tt1)/num_qu)

    elif cfg.RET.LQUEXP.TYPE == 'none':
        pass

    else:
        raise ValueError('Uknown type %s' % (cfg.RET.LQUEXP.TYPE))

    return retrievals, retrieval_time


def pos_neg_feature(featureExtractor, query_data, prop_data, info_vec_qu,
                    retrievals_ret_r, retrievals_ret_f,  dataset, cfg):

    """ Extract pos and neg annotated features """

    retrievals_ret_r_mean = np.mean([len(ret) for ret in retrievals_ret_r])
    retrievals_ret_f_mean = np.mean([len(ret) for ret in retrievals_ret_f])
    logging.info(f'#corrections: correct {retrievals_ret_r_mean}, false {retrievals_ret_f_mean}')

    # - extract features of corrected patches
    query_data_ret = utils.get_query_from_retrieval(retrievals_ret_r, info_vec_qu, dataset, cfg)
    # - concatenate with original query
    query_data_ret = utils.concat_query_data(query_data, query_data_ret)
    (features_qu_ret,
     info_vec_qu_ret,
     num_votes_qu_ret,
     features_v_ret,
     shift_v_ret,
     t_overall_query) = query_feature(featureExtractor,
                                      query_data_ret,
                                      prop_data,
                                      dataset,
                                      cfg.RET.RETRAIN.VOTING,
                                      cfg)

    query_data_ret_f = utils.get_query_from_retrieval(retrievals_ret_f, info_vec_qu, dataset, cfg)
    (features_qu_ret_f,
     info_vec_qu_ret_f,
     num_votes_qu_ret_f,
     features_v_ret_f,
     shift_v_ret_f,
     t_overall_query_f) = query_feature(featureExtractor,
                                        query_data_ret_f,
                                        prop_data,
                                        dataset,
                                        cfg.RET.RETRAIN.VOTING,
                                        cfg)

    return (features_qu_ret, info_vec_qu_ret, num_votes_qu_ret, features_v_ret, shift_v_ret,
            features_qu_ret_f, info_vec_qu_ret_f)


def retrieval_voting_ret(index,
                         info_vec,
                         info_vec_imgrange,
                         pqRecon,
                         pqReconhdf5,
                         features_qu_ret,
                         info_vec_qu_ret,
                         features_qu_ret_f,
                         info_vec_qu_ret_f,
                         info_vec_qu,
                         num_votes_qu_ret,
                         features_v_ret,
                         shift_v_ret,
                         img_neg,
                         feat_pool,
                         dataset,
                         cfg,
                         ret_name=''):

    tfaiss_1 = time.time()
    retrievals = {}
    retrieval_time = []

    img_neg_ret = img_neg

    # - train svm
    logging.info('Train exemplar queris ... ')
    t1 = time.time()
    # - initialize examplars
    features_qu = np.zeros([info_vec_qu.shape[0], features_qu_ret.shape[1]])
    # - sample negatives
    featneg_pool = feat_pool
    np.random.seed(12)
    idxrand = np.random.choice(featneg_pool.shape[0], min(100, featneg_pool.shape[0]), replace=False)
    featneg_pool = featneg_pool[idxrand, :]
    # - loop over all queries
    for qid in info_vec_qu[:, 0]:
        idx_tmp_f = np.where(info_vec_qu_ret_f[:, 0] == qid)[0]
        if idx_tmp_f.shape[0] != 0:
            features_f = features_qu_ret_f[idx_tmp_f, :].reshape(idx_tmp_f.shape[0], features_qu_ret_f.shape[1])
            featneg = np.concatenate((features_f, featneg_pool), axis=0)  # concatenate feature
        else:
            featneg = featneg_pool
        # - train svm classifier
        idx_tmp = np.where(info_vec_qu_ret[:, 0] == qid)[0]
        features_train = np.concatenate((features_qu_ret[idx_tmp, :].reshape(idx_tmp.shape[0], -1), featneg), axis=0)  # concatenate feature
        labels_train = [0] * idx_tmp.shape[0] + [1] * len(featneg)  # define labels
        svm_linear = LinearSVC(random_state=0, class_weight='balanced')
        svm_linear.fit(features_train, labels_train)
        svm_linear_w = svm_linear.coef_
        features_qu[qid, :] = - svm_linear_w
        if ((qid + 1) % 10) == 0:
            logging.info(
                'Train exemlar svm %d/%d: %3.2f seconds' % (qid + 1, features_qu_ret.shape[0], time.time() - t1))

    num_qu = features_qu.shape[0]

    tt1 = time.time()
    nn_dist, nn_idx = index.search(features_qu.astype('float32').copy(), cfg.RET.FAISS.NUM_KNN)
    # - remove based on negatives
    utils.index_filter_neg(nn_dist, nn_idx, img_neg_ret, info_vec)
    utils.index_filter_pos(nn_dist, nn_idx, info_vec, info_vec_qu_ret, cfg)
    nn_dist = utils.normalize_dist(nn_dist)

    # - compute voting vector for nn proposal of query in query image
    shift_qu = np.zeros([features_qu_ret.shape[0], 3])
    for qi in range(features_qu_ret.shape[0]):
        img_id = info_vec_qu_ret[qi][1]
        img_size = dataset['imagesizes'][img_id] / np.max(dataset['imagesizes'][img_id])
        bbs_qu_rel = info_vec_qu_ret[qi][2:6] / cfg.RET.INFOVEC.BBSSCALE
        bbs_qu = bbs_qu_rel * [img_size[1], img_size[0], img_size[1], img_size[0]]
        qi_mod = info_vec_qu_ret[qi, 0]
        idx_tmp = np.where(info_vec[nn_idx[qi_mod, :], 1] == img_id)[0]
        if idx_tmp.shape[0] != 0:
            # - hit in originating image
            bbs_ret_rel = info_vec[nn_idx[qi_mod, idx_tmp[0]], 2:6].reshape(1, -1) / cfg.RET.INFOVEC.BBSSCALE
            bbs_ret = bbs_ret_rel * [img_size[1], img_size[0], img_size[1], img_size[0]]
        else:
            # - not hit in originating image
            bbs_ret = bbs_qu
        shift_qu[qi, :] = utils.get_shift_vec(torch.Tensor(bbs_ret.squeeze()), torch.Tensor(bbs_ret.reshape(1, -1))).cpu().numpy()
    # - take mean of voting vectors
    shift_qu = utils.mean_aggregate(shift_qu.copy(), info_vec_qu_ret[:, 0], normalize=False)

    # - convert results to retrieval vec
    retrievals_tmp = utils.get_retrievals(nn_idx, nn_dist, info_vec, info_vec_qu[:, 0], cfg)
    retrieval_time.append((time.time()-tt1)/num_qu)

    if cfg.RET.RETRAIN.VOTING.FLAG:
        if features_v_ret.shape[0] != 0:
            tt1 = time.time()
            idx_tmp = np.zeros(features_v_ret.shape[0]).astype(np.int)
            for qid_tmp in range(info_vec_qu_ret.shape[0]):
                qi_org = info_vec_qu_ret[qid_tmp, 0]
                idx_range = list(range(np.sum(num_votes_qu_ret[0:(qid_tmp+1)]), np.sum(num_votes_qu_ret[0:(qid_tmp+2)])))
                idx_tmp[idx_range] = qi_org
            nn_dist_v, nn_idx_v = index.search(features_v_ret.astype('float32').copy(), cfg.RET.FAISS.NUM_KNN)
            nn_dist_v = utils.normalize_dist(nn_dist_v)
            # remove based on negatives
            if img_neg:
                img_neg_v = [img_neg[i] for i in idx_tmp]
                utils.index_filter_neg(nn_dist_v, nn_idx_v, img_neg_v, info_vec)
                utils.index_filter_pos(nn_dist_v, nn_idx_v, info_vec, info_vec_qu_ret, cfg)
        else:
            nn_idx_v = np.array([]).reshape(0, 2)
            nn_dist_v = np.array([]).reshape(0, 2)
            shift_v_ret = np.array([]).reshape(0, 2)
        # - voting
        nn_idx, nn_dist, nn_idx_v, nn_dist_v, retrievals_tmp = voting_cython.vote_ret(nn_idx,
                                                                                      nn_dist,
                                                                                      info_vec,
                                                                                      info_vec_imgrange,
                                                                                      info_vec_qu,
                                                                                      info_vec_qu_ret,
                                                                                      nn_idx_v,
                                                                                      nn_dist_v,
                                                                                      shift_v_ret,
                                                                                      shift_qu,
                                                                                      num_votes_qu_ret,
                                                                                      dataset,
                                                                                      cfg)

        retrieval_time.append((time.time()-tt1)/num_qu)
        # - save retrievlas
        retrievals[f'{ret_name}_0'] = retrievals_tmp
        logging.info('Faiss retrieval took: %3.2f sec' % (time.time()-tfaiss_1))

    # ----------------------------------------------------------------------
    # QUREY EXPANSION using NN
    # ----------------------------------------------------------------------
    if cfg.RET.RETRAIN.LQUEXP.TYPE == 'none':
        pass

    elif cfg.RET.RETRAIN.LQUEXP.TYPE == 'nn':
        tt1 = time.time()
        # - filter nn_idx, nn_idx_v
        nn_idx_qe, nn_dist_qe = utils.filter_singlehit_perimage(nn_idx, nn_dist, info_vec)
        if cfg.RET.RETRAIN.VOTING.FLAG:
            nn_idx_v_qe, nn_dist_v_qe = utils.filter_singlehit_perimage(nn_idx_v, nn_dist_v, info_vec)
        # - if several rounds of query expansion
        for r in range(len(cfg.RET.RETRAIN.LQUEXP.NUM)):
            tqe1 = time.time()
            logging.info('-- Query expansion round: %d' % (r))
            # - get all features
            features_qu_qe = np.zeros_like(features_qu)
            for qid in range(nn_idx_qe.shape[0]):
                nn_idx_tmp = nn_idx_qe[qid, :].copy()  # changes over query expansion rounds
                nn_idx_tmp = nn_idx_tmp[0:cfg.RET.RETRAIN.LQUEXP.NUM[r]].copy()
                nn_idx_tmp = nn_idx_tmp[nn_idx_tmp != -1]
                f_qu = features_qu[qid, :].reshape(1, -1)  # original query
                # - reconstruct features for query expansion
                f_nn = pqRecon.pq.decode(pqReconhdf5['features'][np.sort(nn_idx_tmp), :])
                f = np.concatenate((f_qu, f_nn), axis=0)
                features_qu_qe[qid, :] = sklearn_normalize(np.mean(f, axis=0).reshape(1, -1), axis=1, norm='l2')
                if cfg.RET.RETRAIN.VOTING.FLAG:
                    if features_v_ret.shape[0] != 0:
                        idx_qi_range = np.where(info_vec_qu_ret[:, 0] == qid)[0]
                        idx_range = [list(range(np.sum(num_votes_qu_ret[0:(qi_tmp+1)]),
                                                np.sum(num_votes_qu_ret[0:(qi_tmp+2)]))) for qi_tmp in idx_qi_range]
                        idx_range = list(np.concatenate(idx_range).astype(np.int32))
                        f_v = features_v_ret[idx_range, :]
                        nn_idx_v_tmp = nn_idx_v_qe[idx_range, 0:cfg.RET.RETRAIN.LQUEXP.NUM[r]]

                        for vid, f_v_qu in enumerate(f_v):
                            nn_idx_v_tmp_tmp = nn_idx_v_tmp[vid, :].copy()
                            nn_idx_v_tmp_tmp  = nn_idx_v_tmp_tmp[nn_idx_v_tmp_tmp != -1]
                            f_v_nn = pqRecon.pq.decode(pqReconhdf5['features'][np.sort(nn_idx_v_tmp_tmp), :])
                            f = np.concatenate([f_v_qu.reshape(1, -1), f_v_nn], axis=0)
                            features_v_ret[idx_range[vid], :] = sklearn_normalize(np.mean(f, axis=0).reshape(1, -1), axis=1, norm='l2')
            # - knn search
            nn_dist_qe, nn_idx_qe = index.search(features_qu_qe.astype('float32'), cfg.RET.FAISS.NUM_KNN)
            utils.index_filter_neg(nn_dist_qe, nn_idx_qe, img_neg_ret, info_vec)
            utils.index_filter_pos(nn_dist_qe, nn_idx_qe, info_vec, info_vec_qu_ret, cfg)  # remove based on negatives
            nn_dist_qe = utils.normalize_dist(nn_dist_qe)
            # - update shift_qu
            shift_qu_qe = np.zeros([features_qu_ret.shape[0], 3])
            for qi in range(features_qu_ret.shape[0]):
                img_id = info_vec_qu_ret[qi][1]
                img_size = dataset['imagesizes'][img_id] / np.max(dataset['imagesizes'][img_id])
                bbs_qu_rel = info_vec_qu_ret[qi][2:6] / cfg.RET.INFOVEC.BBSSCALE
                bbs_qu = bbs_qu_rel * [img_size[1], img_size[0], img_size[1], img_size[0]]
                qi_mod = info_vec_qu_ret[qi, 0]
                idx_tmp = np.where(info_vec[nn_idx_qe[qi_mod, :], 1] == img_id)[0]
                if idx_tmp.shape[0] != 0:
                    # - hit in originating image -> update
                    bbs_ret_rel = info_vec[nn_idx_qe[qi_mod, idx_tmp[0]], 2:6].reshape(1, -1) / cfg.RET.INFOVEC.BBSSCALE
                    bbs_ret = bbs_ret_rel * [img_size[1], img_size[0], img_size[1], img_size[0]]
                    shift_qu_qe[qi, :] = utils.get_shift_vec(torch.Tensor(bbs_qu), torch.Tensor(bbs_ret.reshape(1, -1))).cpu().numpy()
            # - aggregate voting vector
            shift_qu_qe = utils.mean_aggregate(shift_qu_qe.copy(), info_vec_qu_ret[:, 0], normalize=False)

            if cfg.RET.RETRAIN.VOTING.FLAG:
                if features_v_ret.shape[0] != 0:
                    # - knn search
                    nn_dist_v_qe, nn_idx_v_qe = index.search(features_v_ret.astype('float32').copy(), cfg.RET.FAISS.NUM_KNN)
                    nn_dist_v_qe = utils.normalize_dist(nn_dist_v_qe)
                    if img_neg:
                        utils.index_filter_neg(nn_dist_v_qe, nn_idx_v_qe, img_neg_v, info_vec)
                        utils.index_filter_pos(nn_dist_v_qe, nn_idx_v_qe, info_vec, info_vec_qu_ret, cfg)
                    # - update shift_v -> shift_v_qe
                    shift_v_qe = np.zeros([nn_idx_v.shape[0], 3])
                    for qi in range(info_vec_qu.shape[0]):
                        img_id = info_vec_qu[qi][1]
                        idx_qi_range = np.where(info_vec_qu_ret[:, 0] == qi)[0]
                        idx_range = [list(range(np.sum(num_votes_qu_ret[0:(qi_tmp+1)]),
                                                np.sum(num_votes_qu_ret[0:(qi_tmp+2)]))) for qi_tmp in idx_qi_range]
                        if len(idx_range) > 0:
                            idx_range = np.concatenate(idx_range).astype(np.int32)
                        bbs_qu_rel = info_vec_qu[qi][2:6] / cfg.RET.INFOVEC.BBSSCALE
                        img_size = dataset['imagesizes'][img_id] / np.max(dataset['imagesizes'][img_id])
                        bbs_qu = bbs_qu_rel * [img_size[1], img_size[0], img_size[1], img_size[0]]
                        for ii in idx_range:
                            idx_tmp = np.where(info_vec[nn_idx_v_qe[ii, :], 1] == img_id)[0]
                            if idx_tmp.shape[0] != 0:
                                # - hit in originating image
                                bbs_ret_rel = info_vec[nn_idx_v_qe[ii, idx_tmp[0]], 2:6].reshape(1, -1) / cfg.RET.INFOVEC.BBSSCALE
                                bbs_ret = bbs_ret_rel * [img_size[1], img_size[0], img_size[1], img_size[0]]
                                shift_v_qe[ii, :] = utils.get_shift_vec(torch.Tensor(bbs_qu), torch.Tensor(bbs_ret.reshape(1, -1))).cpu().numpy()
                            else:
                                shift_v_qe[ii, :] = shift_v_ret[ii, :]
                else:
                    nn_idx_v_qe = np.array([]).reshape(0, 2)
                    nn_dist_v_qe = np.array([]).reshape(0, 2)
                    shift_v_qe = np.array([]).reshape(0, 2)
                # - voting
                nn_idx_qe, nn_dist_qe, nn_idx_v_qe, nn_dist_v_qe, retrievals_qe_tmp = voting_cython.vote_ret(nn_idx_qe,
                                                                                                             nn_dist_qe,
                                                                                                             info_vec,
                                                                                                             info_vec_imgrange,
                                                                                                             info_vec_qu,
                                                                                                             info_vec_qu_ret,
                                                                                                             nn_idx_v_qe,
                                                                                                             nn_dist_v_qe,
                                                                                                             shift_v_qe,
                                                                                                             shift_qu_qe,
                                                                                                             num_votes_qu_ret,
                                                                                                             dataset,
                                                                                                             cfg,
                                                                                                             vote_name=('_qe_%d' % r))
            else:
                # - convert results to retrieval vec
                retrievals_qe_tmp = utils.get_retrievals(nn_idx_qe, nn_dist_qe, info_vec, cfg)
            retrievals[f'{ret_name}_qe_%d' % r] = retrievals_qe_tmp
            logging.info('-- Query expansion round %d took %3.2f sec' % (r, time.time() - tqe1))
        retrieval_time.append((time.time()-tt1)/num_qu)
    else:
        raise ValueError('Uknown type %s' % (cfg.RET.RETRAIN.LQUEXP.TYPE))

    return retrievals, retrieval_time




