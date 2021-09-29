import numpy as np
import os
import os.path as osp
from easydict import EasyDict as edict
import time
import pandas as pd
import h5py
import logging
import json
import pickle
import deepdish
import ast
from sklearn.manifold import TSNE
import torch

from src import datasets, feature_reduction, retrieval, retrieval_geometry, utils
from src import faiss_indices, get_filenames, proposals_cython, style_templates, style_transformations
from networks import init_network


IMAGE_FILE_FORMATS = ['.jpg', '.jpeg', '.jpe', '.jif', '.jfif', '.jfi', '.png', '.tiff', '.tif']


def initialization(cfg_input, gpus=[]):
    """ Offline preparation stage: initialization of search index """

    t1_init = time.time()

    # - loading config file
    if type(cfg_input) == dict:
        cfg = edict(cfg_input)
    else:
        try:
            with open(cfg_input, 'r') as f:
                cfg = edict(json.load(f))
        except:
            raise ValueError(f'Invalid input type: {type(cfg_input)}')

    # - fix initialization to cpu
    cfg.RET.FAISS.GPU = False

    # - convert all images to .jpg
    logging.info("Image conversion to .jpg")
    utils.convert_images(osp.join(cfg.DATA_DIR, 'images'), IMAGE_FILE_FORMATS)

    # --------------------------------------------------------------
    # Initialize Dataset
    # --------------------------------------------------------------
    dataset = datasets.init_dataset_interface(cfg)
    utils.adjust_discprop(cfg, dataset)

    # --------------------------------------------------------------
    # Extract Style Templates
    # --------------------------------------------------------------
    # --------------------------------------------------------------
    t1 = time.time()
    logging.info("Comptue style templates ...")
    style_templates.compute_style_templates(dataset, cfg)
    logging.info('Compute style template took: %3.2f sec' % (time.time()-t1))

    # --------------------------------------------------------------
    # Perform Style Transformations
    # --------------------------------------------------------------
    t1 = time.time()
    logging.info("Style transfers ...")
    style_transformations.generate_style_transformations(dataset, cfg)
    logging.info('Style transfers took: %3.2f sec' % (time.time()-t1))

    # --------------------------------------------------------------
    # REGION PROPOSALS
    # --------------------------------------------------------------
    t1 = time.time()
    logging.info('Proposal extraction ...')
    if cfg.RET.ROI.TYPE in ['sw']:
        prop_path = utils.create_dir(osp.join(cfg.OUTPUT_DIR, 'initialization', 'proposals'))
        prop_filename = get_filenames.proposalsFilename(cfg)
        if osp.exists(osp.join(prop_path, prop_filename)) & cfg.RET.SAVELOAD.ROIS_LOAD:
            # - load image proposals
            prop_data = deepdish.io.load(osp.join(prop_path, prop_filename))
        else:
            # - compute image proposals
            logging.info("Extract proposal type: %s" % cfg.RET.ROI.TYPE)
            prop_data = proposals_cython.extract_sliding_window(dataset, cfg, include_gt='exclude')
            for key in prop_data.keys():
                prop_data[key] = np.asarray(prop_data[key])
            # - save image proposals
            if cfg.RET.SAVELOAD.ROIS_SAVE:
                t_prop_save = time.time()
                logging.info('Saving proposal data ...')
                deepdish.io.save(osp.join(prop_path, prop_filename), prop_data)
                logging.info('Saving proposal data took %3.2f sec' % (time.time() - t_prop_save))

    logging.info("Average number of proposals: %d" % (prop_data['info_vec'].shape[0] / len(prop_data['img_ids'])))
    logging.info('Proposal extraction took: %3.2f sec' % (time.time()-t1))

    # --------------------------------------------------------------
    # NETWORK INITIALIZATION
    # --------------------------------------------------------------
    t1 = time.time()
    logging.info('Network initialization ...')
    featureExtractor = init_network.init(cfg)
    featureExtractor.create_architecture()
    if cfg.RET.CUDA:
        featureExtractor.cuda()
    # - set model to evaluation mode
    for param in featureExtractor.parameters():
        param.requires_grad = False
    # - set evaluation mode
    featureExtractor.eval()
    logging.info('Network initialization took: %3.2f sec' % (time.time()-t1))
    if gpus:
        logging.info('GPU Memory: ' + gpus.reportstr())

    torch.cuda.get_device_name()
    torch.cuda.is_available()

    # -------------------------------------------
    # PCA FEATURE REDUCTION MODEL
    # -------------------------------------------
    if cfg.RET.FEAT_REDUCT.TYPE != 'none':
        tt1 = time.time()
        logging.info('Train feature reduction model ...')
        featred_model = feature_reduction.compute_pca(featureExtractor, prop_data, dataset, cfg)
        logging.info('Train feature reduction model took: %3.2f sec' % (time.time()-tt1))
        featureExtractor._set_featred_model(featred_model)  # - applay feature reduction to extraction model
        torch.cuda.empty_cache()
    else:
        featred_model = []

    # ---------------------------------------
    # GENERATE INDEX FOR FAST RETRIEVAL
    # ---------------------------------------
    _, _, _, _ = faiss_indices.generate_index(featureExtractor, prop_data, dataset, gpus, cfg)

    # - open pqhdf5 for reconstruction
    t1 = time.time()
    pqReconh5_file = osp.join(osp.join(cfg.OUTPUT_DIR, 'initialization', 'pqRecon'),
                              get_filenames.pqReconh5Filename_exp(cfg))
    pqReconhdf5 = h5py.File(pqReconh5_file, 'r')
    logging.info('Time for opening hdf5 file: %3.2f sec' % (time.time() - t1))
    logging.info('Initialization took overall: %3.2f sec' % (time.time() - t1_init))
    return 0


# -----------------------------
# Variables hold in memory
# -----------------------------
dataset = None
image_dict = None
image_dict_inv = None
prop_data = None
featureExtractor = None
index = None
info_vec = None
info_vec_imgrange = None
pqRecon = None
pqReconhdf5 = None
feat_pool = None

def load_initialisation(index_path, cfg, gpus):
    """ Load initializations """

    global dataset, image_dict, image_dict_inv, prop_data, featureExtractor, index, \
        info_vec, info_vec_imgrange, pqRecon, pqReconhdf5, feat_pool

    # --------------------------------------------------------------
    # Initialize Dataset
    # --------------------------------------------------------------
    dataset = datasets.init_dataset_interface(cfg)
    utils.adjust_discprop(cfg, dataset)

    # - load index image list
    with open(osp.join(index_path, 'image_list.json')) as f:
        image_list = json.load(f)
    image_dict = {k['id']: k['filename'] for k in image_list}
    image_dict_inv = {v: k for (k, v) in image_dict.items()}

    # --------------------------------------------------------------
    # REGION PROPOSALS
    # --------------------------------------------------------------
    t1 = time.time()
    if cfg.RET.ROI.TYPE in ['sw']:
        prop_path = utils.create_dir(osp.join(cfg.OUTPUT_DIR, 'initialization', 'proposals'))
        prop_filename = get_filenames.proposalsFilename(cfg)
        if osp.exists(osp.join(prop_path, prop_filename)) & cfg.RET.SAVELOAD.ROIS_LOAD:
            prop_data = deepdish.io.load(osp.join(prop_path, prop_filename))
        else:
            # - compute image proposals
            logging.info("Extract proposal type: %s" % cfg.RET.ROI.TYPE)
            prop_data = proposals_cython.extract_sliding_window(dataset, cfg, include_gt='exclude')
            for key in prop_data.keys():
                prop_data[key] = np.asarray(prop_data[key])
            # - save image proposals
            if cfg.RET.SAVELOAD.ROIS_SAVE:
                t_prop_save = time.time()
                logging.info('Saving proposal data ...')
                with open(osp.join(prop_path, prop_filename), 'wb') as file:
                    pickle.dump(prop_data, file)
                logging.info('Saving proposal data took %3.2f sec' % (time.time() - t_prop_save))

    logging.info("Average number of proposals: %d" % (prop_data['info_vec'].shape[0] / len(prop_data['img_ids'])))
    logging.info('Proposal extraction took: %3.2f sec' % (time.time()-t1))
    if gpus:
        logging.info('GPU Memory: ' + gpus.reportstr())

    # --------------------------------------------------------------
    # NETWORK INITIALIZATION
    # --------------------------------------------------------------
    t1 = time.time()

    featureExtractor = init_network.init(cfg)
    featureExtractor.create_architecture()
    if cfg.RET.CUDA:
        featureExtractor.cuda()
    # - set model to evaluation mode
    for param in featureExtractor.parameters():
        param.requires_grad = False
    # - set evaluation mode
    featureExtractor.eval()
    logging.info('Network initialization took: %3.2f sec' % (time.time()-t1))
    if gpus:
        logging.info('GPU Memory: ' + gpus.reportstr())

    # -------------------------------------------
    # PCA FEATURE REDUCTION MODEL
    # -------------------------------------------
    if cfg.RET.FEAT_REDUCT.TYPE != 'none':
        tt1 = time.time()
        featred_model = feature_reduction.compute_pca(featureExtractor, [], dataset, cfg)
        torch.cuda.empty_cache()
        logging.info('Train feature reduction model took: %3.2f sec' % (time.time()-tt1))
        if gpus:
            logging.info('GPU Memory: ' + gpus.reportstr())
    else:
        featred_model = []

    # - applay feature reduction to extraction model 1
    if cfg.RET.FEAT_REDUCT.TYPE != 'none':
        featureExtractor._set_featred_model(featred_model)

    # ---------------------------------------
    # GENERATE INDEX FOR FAST RETRIEVAL
    # ---------------------------------------
    index, info_vec, info_vec_imgrange, pqRecon = faiss_indices.generate_index(featureExtractor, [], dataset, gpus, cfg)

    # - open pqhdf5 for reconstruction
    t_h5open = time.time()
    pqReconh5_file = osp.join(osp.join(cfg.OUTPUT_DIR, 'initialization', 'pqRecon'), get_filenames.pqReconh5Filename_exp(cfg))
    pqReconhdf5 = h5py.File(pqReconh5_file, 'r')
    logging.info('Time for opening hdf5 file: %3.2f sec' % (time.time() - t_h5open))

    # - load feature pool for retraining
    feat_pool_path = utils.create_dir(osp.join(cfg.OUTPUT_DIR, 'initialization', 'featpool'))
    feat_pool_filename = get_filenames.featredpool2Filename(cfg)
    feat_pool = feature_reduction.sample_feature_pool([], [], [], cfg,
                                                      filename=osp.join(feat_pool_path, feat_pool_filename),
                                                      num_sample_images=cfg.RET.FEATPOOL2.NUM_IMAGE,
                                                      num_sample_patches=cfg.RET.FEATPOOL2.NUM_PATCH)
    logging.info('Loading finished ...')




def get_queries(config_file):
    """
    Reading queries saved by the web-interface
    :param path: path to the search directory retrieval/search_x
    :return: query dictionary
    """
    assert(osp.exists(config_file))
    # - loading config
    config = json.load(open(config_file, 'r'))

    ## QUERY
    queries_tmp = {}
    if 'root_path' in config.keys():
        queries_tmp['root_path'] = config['root_path']
    else:
        queries_tmp['root_path'] = ''
    queries_tmp['data'] = [{}]
    queries_tmp['data'][-1]['bbs'] = config['boxes']

    # - negatives: convert box_data -> bbs, string -> lists / floats
    if 'negatives' in config.keys():
        for neg in config['negatives']:
            neg['bbs'] = eval(neg['refined_searchbox'])
            neg['img_id'] = eval(neg['image_id'])
            neg['id'] = eval(neg['id'])
    else:
        config['negatives'] = []
    queries_tmp['data'][-1]['negatives'] = config['negatives']

    # - positives: convert box_data -> bbs, string -> lists / floats
    if 'positives' in config.keys():
        for pos in config['positives']:
            pos['bbs'] = eval(pos['refined_searchbox'])
            pos['id'] = eval(pos['id'])
            pos['img_id'] = eval(pos['image_id'])
    else:
        config['positives'] = []
    queries_tmp['data'][-1]['positives'] = config['positives']

    queries_tmp['data'][-1]['img_id'] = config['image']
    if 'orig_filename' in config.keys():
        queries_tmp['data'][-1]['orig_filename'] = config['image']
    if 'qu_id' in config.keys():
        queries_tmp['data'][-1]['qu_id'] = config['qu_id']
    #
    return queries_tmp


def search(cfg_file, search_id):
    """
    Search function: performs search and saves results as .json for api
    :param cfg_file: configuration file
    :param search_id: search index
    """

    include_identical = True

    index_path = '/'.join(cfg_file.split('/')[:-1])
    search_path = osp.join(index_path, f'retrieval/search_{search_id}')
    search_cfg_file = osp.join(search_path, 'config.json')

    # - loading config file
    try:
        with open(cfg_file, 'r') as f:
            cfg = edict(json.load(f))
    except:
        raise ValueError(f'Invalid input type: {type(cfg_file)}')

    gpus = []
    # - loading initialization
    if not index:
        logging.info("------------------------- Initialization -------------------------")
        load_initialisation(index_path, cfg, gpus)

    # - load query information
    try:
        with open(search_cfg_file, 'r') as f:
            search_input = edict(json.load(f))
    except:
        raise ValueError(f'Invalid input type: {type(cfg_file)}')

    # ----------------------------------------------------------------------
    # GENERATE QUERY FEATURE OF DATASET
    # ----------------------------------------------------------------------
    # - get queries
    query_data, query_data_pos, query_data_neg = utils.get_query_data(search_input, image_dict, dataset, cfg)
    # - extact features
    features_qu, \
    info_vec_qu, \
    num_votes_qu, \
    features_v, \
    shift_v, \
    t_overall = retrieval.query_feature(featureExtractor,
                                        query_data,
                                        prop_data,
                                        dataset,
                                        cfg.RET.VOTING,
                                        cfg)



    # USER FEEDBACK
    if query_data_pos['img_ids']:
        # - concatenate with original query
        query_data_pos = utils.concat_query_data(query_data, query_data_pos)
        # - extract query & pos features
        features_qu_ret, \
        info_vec_qu_ret, \
        num_votes_qu_ret, \
        features_v_ret, \
        shift_v_ret, \
        t_overall_query = retrieval.query_feature(featureExtractor,
                                                  query_data_pos,
                                                  prop_data,
                                                  dataset,
                                                  cfg.RET.RETRAIN.VOTING,
                                                  cfg)
        if query_data_neg['info_vec'].shape[0]:
            # - extract negative retrieval features
            features_qu_ret_f, \
            info_vec_qu_ret_f, \
            num_votes_qu_ret_f, \
            features_v_ret_f, \
            shift_v_ret_f, \
            t_overall_query_f = retrieval.query_feature(featureExtractor,
                                                        query_data_neg,
                                                        prop_data,
                                                        dataset,
                                                        cfg.RET.RETRAIN.VOTING,
                                                        cfg)
            img_neg = list(info_vec_qu_ret_f[:, 1])
        else:
            # - no negatives marked
            features_qu_ret_f = []
            info_vec_qu_ret_f = []
            info_vec_qu_ret_f = -1 * np.ones([1, 8])
            img_neg = []

        retrievals, retrieval_time = retrieval.retrieval_voting_ret(index,
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
                                                                    ret_name=f'')

    # NO USER FEEDBACK
    else:
        retrievals, retrieval_time = retrieval.retrieval_voting(index,
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
                                                                cfg)

    cfg.RET.CONTEXT = edict()
    cfg.RET.CONTEXT.MODE = search_input['params']['combination']
    cfg.RET.CONTEXT.WEIGHTS = search_input['params']['weights']

    # - select retrieval after local query expansion
    if '_qu_0' in retrievals.keys():
        retrievals = retrievals['_qe_0']
    else:
        retrievals = retrievals['_0']

    # - restrict to top 10 hits per image
    ret_tmp = [[] for i in range(len(retrievals))]
    for qi in range(len(retrievals)):
        img_ret = []
        for i, ret in enumerate(retrievals[qi]):
            if img_ret.count(ret[0]) >= 10:
                continue
            else:
                img_ret.append(ret[0])
                ret_tmp[qi].append(ret)
        ret_tmp[qi] = np.array(ret_tmp[qi])
    retrievals = ret_tmp

    # - remove query image from list of retrievals
    if not include_identical:
        for qi, img_id in enumerate(info_vec_qu[:, 1]):
            retrievals[qi] = np.delete(retrievals[qi], np.where(retrievals[qi][:, 0] == img_id), axis=0)

    # - retrievals: convert to original image coordinates
    for qi, ret in enumerate(retrievals):
        for ri, r in enumerate(ret):
            # - transform to original image space
            img_size_org = dataset['imagesizes'][int(r[0])]
            scale = cfg.RET.IMG.MINSIZE / min(img_size_org)
            img_size = dataset['imagesizes'][int(r[0])] * scale + 2 * cfg.RET.IMG.PADDING * np.ones([2])
            bbs_ret = r[1:5] * np.array([img_size[1], img_size[0], img_size[1], img_size[0]])
            bbs_ret -= cfg.RET.IMG.PADDING * np.ones([4])
            bbs_ret /= scale
            bbs_ret = [max(int(bbs_ret[0]), 0),
                       max(int(bbs_ret[1]), 0),
                       min(int(bbs_ret[2]), img_size_org[1]),
                       min(int(bbs_ret[3]), img_size_org[0])]
            retrievals[qi][ri][1:5] = bbs_ret
        retrievals[qi] = retrievals[qi].tolist()

    # - queries: convert to original image coordinates
    bbs_qu = []
    for i, v in enumerate(info_vec_qu):
        img_size_org = dataset['imagesizes'][v[1]]
        scale = cfg.RET.IMG.MINSIZE / min(img_size_org)
        img_size = img_size_org * scale + 2 * cfg.RET.IMG.PADDING * np.ones([2])
        bbs_qu_tmp = v[2:6] / cfg.RET.INFOVEC.BBSSCALE * np.array([img_size[1], img_size[0], img_size[1], img_size[0]])
        bbs_qu_tmp -= cfg.RET.IMG.PADDING * np.ones([4])
        bbs_qu_tmp /= scale
        bbs_qu_tmp = [max(int(bbs_qu_tmp[0]), 0),
                      max(int(bbs_qu_tmp[1]), 0),
                      min(int(bbs_qu_tmp[2]), img_size_org[1]),
                      min(int(bbs_qu_tmp[3]), img_size_org[0])]
        bbs_qu.append(bbs_qu_tmp)
    bbs_qu = np.array(bbs_qu)

    # - retrievals
    ret_bbs, ret_img, ret_score, ret_idx = [], [], [], []
    for qi, ret_qi in enumerate(retrievals):
        ret_img.append([int(ret[0]) for ret in ret_qi])
        ret_bbs.append([ret[1:5] for ret in ret_qi])
        ret_score.append([ret[5] for ret in ret_qi])
        ret_idx.append([ret[6] for ret in ret_qi])

    # - similarity -> distance
    max_sim = np.max(np.max(ret_score))
    for qi, ret_qi in enumerate(retrievals):
        ret_score[qi] = [max_sim - s for s in ret_score[qi]]

    img_size_qu = dataset['imagesizes_pad'][info_vec_qu[0, 1], :]
    img_sizes = dataset['imagesizes_pad']

    ret_img_context, \
    ret_num_bbs_context, \
    ret_bbs_context, \
    ret_score_single, \
    ret_score_context, \
    idx_return = retrieval_geometry.retrieval_geometry(bbs_qu.copy(),
                                                       img_size_qu,
                                                       ret_img.copy(),
                                                       img_sizes,
                                                       ret_bbs.copy(),
                                                       ret_score.copy(),
                                                       ret_idx.copy(),
                                                       cfg)

    # - only top results
    max_res = 100
    ret_img_context = ret_img_context[0:max_res]
    ret_bbs_context = ret_bbs_context[0:max_res]
    ret_score_single = ret_score_single[0:max_res]
    ret_score_context = ret_score_context[0:max_res]
    idx_return = idx_return[0:max_res, :]
    #
    ret_img_name_context = [dataset['imagelist'][i] for i in ret_img_context]
    ret_img_id_context = [image_dict_inv[r] for r in ret_img_name_context]
    ret_labels = len(ret_img_name_context) * [-1]
    #
    ret_score_context = [round(s, 1) for s in ret_score_context]
    ret_score_single = [[round(s, 1) for s in sub] for sub in ret_score_single]
    retrieval_output = [list(a) for a in zip(ret_img_id_context, ret_bbs_context, ret_score_single, ret_score_context, ret_labels)]
    # - normalize wrt image width / height in range [0,100] for interface
    for i, ret in enumerate(retrieval_output):
        img_id = dataset['imagelist'].index(image_dict[ret[0]])
        h, w = dataset['imagesizes'][img_id]
        ret[1] = [[round(max(r[0]/w*100, 0.), 2),
                   round(max(r[1]/h*100, 0), 2),
                   round(min(r[2]/w*100, 100.), 2),
                   round(min(r[3]/h*100, 100.), 2)] for r in ret[1]]

    # - replace positives
    num_pos = len(search_input['positives'])
    if num_pos > 0:
        min_score_single = retrieval_output[0][2]
        min_score_context = retrieval_output[0][3]
        img_ids_pos = set([int(search_input['positives'][i]['image_id']) for i in range(num_pos)])
        img_ids_keep = [i for i in range(len(retrieval_output)) if (retrieval_output[i][0] not in img_ids_pos)]
        img_ids_remove = [i for i in range(len(retrieval_output)) if (retrieval_output[i][0] in img_ids_pos)]
        idx_return = np.concatenate([idx_return[img_ids_remove, :], idx_return[img_ids_keep, :]], axis=0)
        retrieval_output = [retrieval_output[i] for i in img_ids_keep]
        img_id_added = []
        for i in range(num_pos-1, -1, -1):
            img_id = int(search_input['positives'][i]['image_id'])
            if not img_id in img_id_added:
                img_id_added.append(img_id)
                bbs = ast.literal_eval(search_input['positives'][i]['refined_searchbox'])
                retrieval_output.insert(0, [img_id, bbs, min_score_single, min_score_context])

    # - prepare output and save in query
    queries = get_queries(search_cfg_file)
    queries['data'][0]['retrievals'] = retrieval_output
    for qu_id, query in enumerate(queries['data']):
        bbs = query['bbs']
        img_id = dataset['imagelist'].index(image_dict[query['img_id']])
        h, w = dataset['imagesizes'][img_id]
        query['bbs'] = [[round(max(bbs[0]/w*100., 0.), 2),
                         round(max(bbs[1]/h*100., 0.), 2),
                         round(min(bbs[2]/w*100., 100.), 2),
                         round(min(bbs[3]/h*100, 100.), 2)] for bbs in query['bbs']]

    # - save query input with rerievals
    with open(osp.join(search_path, 'retrievals.json'), 'w') as fp:
        json.dump(queries, fp)

    # 2D Mapping
    if True:
        projection_origin = [0.5, 0.5]
        idx_return_rep = idx_return.copy()
        idx_return_rep[idx_return_rep == -1] = 0
        # - reconstruct feature vectors
        idx_return_flat = idx_return.reshape(-1)
        idx_return_rep_flat = idx_return_rep.reshape(-1)
        idx_return_rep_flat_rep = idx_return_rep_flat.copy()
        # - remove -1 with 0 -> i.e.
        idx_return_rep_flat_rep[idx_return_rep_flat_rep == -1] = 0
        idx_unique, idx_unique_inv = np.unique(idx_return_rep_flat, return_inverse=True)
        f_ret = pqRecon.pq.decode(pqReconhdf5['features'][idx_unique, :])[idx_unique_inv]
        f_ret[idx_return_flat == -1, :] = np.ones([1, f_ret.shape[1]])  # - part without retrieval in image
        f_ret = f_ret / np.sqrt(np.sum(f_ret ** 2, axis=1)).reshape(-1, 1)  # - normalize
        f_ret = np.expand_dims(f_ret, axis=1).reshape(idx_return.shape[0], idx_return.shape[1], f_ret.shape[1])
        f_ret = f_ret.reshape(f_ret.shape[0], -1)  # - concatenate along axis
        # - compute tsne embedding
        try:
            f_embedding = TSNE(n_components=2).fit_transform(f_ret)
        except:
            # - catch error -> place everything to the center
            f_embedding = np.array([0.5, 0.5]) * np.ones([f.shape[0], 2])

        # - set query to  (0,0)
        center = f_embedding[0, :]
        f_embedding = f_embedding - center
        f_embedding[:, 0] = projection_origin[0] * 0.8 * f_embedding[:, 0] / (np.max(np.abs(f_embedding[:, 0])) + 1e-12)
        f_embedding[:, 1] = projection_origin[1] * 0.8 * f_embedding[:, 1] / (np.max(np.abs(f_embedding[:, 1])) + 1e-12)
        f_embedding = f_embedding + np.array([0.5, 0.5])
        f_embedding_ret = f_embedding
        f_embedding_qu = f_embedding[0]

        # - save as queries
        for i in range(f_embedding_ret.shape[0]):
            queries['data'][0]['retrievals'][i].append(list(f_embedding_ret[i]))
        # - save tsne embedding
        with open(osp.join(search_path, 'retrievals.json'), 'w') as fp:
            json.dump(queries, fp)
        # - save query position in config
        with open(osp.join(search_path, 'config.json'), 'r') as f:
            data = json.load(f)
            data['map_coord'] = f_embedding_qu.tolist()
        with open(osp.join(search_path, 'config.json'), 'w') as f:
            json.dump(data, f)

    logging.info("Search finished.")
    return 0








