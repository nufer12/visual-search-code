import sys, os
import os.path as osp
import numpy as np
import pandas as pd
from PIL import Image
import torch
import torch.nn.functional as F
import ast


# -- load ground truth csv file
def list_converter(instr):
    return list(np.fromstring(instr[1:-1], sep=', '))


def list_converter_int(instr):
    return list(np.fromstring(instr[1:-1], sep=', ').astype(np.int))


def read_gt_csv(csv_file):
    """ Load gt csv file """
    return pd.read_csv(csv_file, converters={'bbs_rel': list_converter,
                                             'img_name': str,
                                             'img_size': list_converter_int})


def create_dir(directory, silent=True):
    """Check if dir exist if not create, return directory name """
    if not os.path.exists(directory):
        os.makedirs(directory)
    elif not silent:
        print('{} already exists ...'.format(directory))
    return directory


def check_dir(directory):
    """Check if dir exist, return directory name"""
    assert(os.path.exists(directory)), 'Path %s is not available' % directory
    return directory


def sizeof(var, suffix='B'):
    num = sys.getsizeof(var)
    for unit in ['', 'Ki', 'Mi', 'Gi', 'Ti', 'Pi', 'Ei', 'Zi']:
        if abs(num) < 1024.0:
            return "%3.1f%s%s" % (num, unit, suffix)
        num /= 1024.0
    return "%.1f%s%s" % (num, 'Yi', suffix)


def pil_loader(path):
    """ open path as file to avoid ResourceWarning """
    with open(path, 'rb') as f:
        img = Image.open(f)
        return img.convert('RGB')


def loadGT(csv_path, cfg, include_padding=False):
    """ Load gt bbx annotation """
    gt_boxes = pd.read_csv(csv_path, converters={'bbs_rel': list_converter,
                                                 'bbs': list_converter,
                                                 'img_size': list_converter,
                                                 'img_name': str}, index_col=False)
    if include_padding:
        for i, box in gt_boxes.iterrows():
            img_size = box['img_size']
            img_pad_org = float(cfg.RET.IMG.PADDING) / float(cfg.RET.IMG.MINSIZE) * float(np.min(img_size[:2]))
            img_size = [s + 2 * img_pad_org for s in img_size]
            bbs = [b + img_pad_org for b in box['bbs']]
            gt_boxes.at[i, 'bbs'] = bbs
            gt_boxes.at[i, 'img_size'] = img_size

    return gt_boxes


def filter_singlehit_perimage(nn_idx, nn_dist, info_vec):
    """ Filter - only one hit per image """
    for q in range(nn_idx.shape[0]):
        img_tmp, idx_tmp = np.unique(info_vec[nn_idx[q, :].reshape(-1), 1], return_index=True)
        idx_sort = np.argsort(nn_dist[q, idx_tmp])
        idx_tmp = idx_tmp[idx_sort]
        nn_idx[q, 0:idx_tmp.shape[0]] = nn_idx[q, idx_tmp]
        nn_dist[q, 0:idx_tmp.shape[0]] = nn_dist[q, idx_tmp]
        nn_idx[q, idx_tmp.shape[0]:] = -1
        nn_dist[q, idx_tmp.shape[0]:] = np.max(nn_dist[q, :])
    return nn_idx, nn_dist


def bbs_rel2abs(bbs_rel, img_size):
    """ Convert relative to absolute bbs coordinates """
    bbs_abs = bbs_rel.copy().reshape(-1, 4)
    for i, bbs_tmp in enumerate(bbs_abs):
        bbs_abs[i, :] = [bbs_tmp[0]*img_size[1],
                         bbs_tmp[1]*img_size[0],
                         bbs_tmp[2]*img_size[1],
                         bbs_tmp[3]*img_size[0]]
    return bbs_abs.reshape(bbs_rel.shape).astype(np.int)


def bbs2center(bbs):
    """ Get bbs center """
    bbs_tmp = bbs.copy().reshape(-1, 4)
    x = (bbs_tmp[:, 2] + bbs_tmp[:, 0]) / 2.
    y = (bbs_tmp[:, 3] + bbs_tmp[:, 1]) / 2.
    if bbs.ndim == 2:
        ct = np.concatenate([x.reshape(-1, 1), y.reshape(-1, 1)], axis=1).reshape(-1, 2)
    else:
        ct = np.concatenate([x.reshape(-1, 1), y.reshape(-1, 1)], axis=1).reshape(2)
    return ct


def bbs_iou_s(boxA, boxB_list):
    """ Compute intersection over union """
    iou_list = []
    for boxB in boxB_list:
        # - determine the coordinates of the intersection rectangle
        xA = max(boxA[0], boxB[0])
        yA = max(boxA[1], boxB[1])
        xB = min(boxA[2], boxB[2])
        yB = min(boxA[3], boxB[3])
        # - compute the area of intersection rectangle
        interArea = max(0, xB - xA + 1) * max(0, yB - yA + 1)
        # - compute the area of both the prediction and ground-truth
        boxAArea = (boxA[2] - boxA[0] + 1) * (boxA[3] - boxA[1] + 1)
        boxBArea = (boxB[2] - boxB[0] + 1) * (boxB[3] - boxB[1] + 1)
        # - compute the intersection over union
        iou_list.append(interArea / float(boxAArea + boxBArea - interArea))
    return iou_list
#

def bbs_iou_torch(boxA, boxBs):
    """ Computer intersection over union """
    iou = torch.zeros([boxBs.shape[0]])
    for i, boxB in enumerate(boxBs):
        # - determine the coordinates of the intersection rectangle
        xA = torch.max(boxA[0], boxB[0])
        yA = torch.max(boxA[1], boxB[1])
        xB = torch.min(boxA[2], boxB[2])
        yB = torch.min(boxA[3], boxB[3])
        # - compute the area of intersection rectangle
        interArea = F.relu(xB - xA) * F.relu(yB - yA)
        if interArea == 0:
            iou[i] = 0
            continue
        # - compute the area of both the prediction and ground-truth
        boxAArea = torch.abs((boxA[2] - boxA[0]) * (boxA[3] - boxA[1]))
        boxBArea = torch.abs((boxB[2] - boxB[0]) * (boxB[3] - boxB[1]))
        # - compute the intersection over union
        iou[i] = interArea / float(boxAArea + boxBArea - interArea)
    return iou


def bbs_inter_torch(boxA, boxBs):
    """ Compute relative intersection """
    inter_rel = torch.zeros([boxBs.shape[0]])
    for i, boxB in enumerate(boxBs):
        # determine coordinates of the intersection rectangle
        xA = torch.max(boxA[0], boxB[0])
        yA = torch.max(boxA[1], boxB[1])
        xB = torch.min(boxA[2], boxB[2])
        yB = torch.min(boxA[3], boxB[3])
        # compute the area of intersection rectangle
        interArea = F.relu(xB - xA ) * F.relu(yB - yA)
        if interArea == 0:
            inter_rel[i] = 0
            continue
        # compute the area of boxB
        boxBArea = torch.abs(boxB[2] - boxB[0]) * torch.abs(boxB[3] - boxB[1])
        # compute relative intersection
        inter_rel[i] = interArea / float(boxBArea)
    return inter_rel


def get_shift_vec(qu, rois):
    """ Compute offset vector of rois to qu """
    rois_diag = torch.sqrt((rois[:, 2] - rois[:, 0])**2 + (rois[:, 3] - rois[:, 1])**2)
    qu_diag = torch.sqrt((qu[2] - qu[0])**2 + (qu[3] - qu[1])**2)
    cx = ((qu[2] + qu[0]) / 2 - (rois[:, 2] + rois[:, 0]) / 2) / rois_diag
    cy = ((qu[3] + qu[1]) / 2 - (rois[:, 3] + rois[:, 1]) / 2) / rois_diag
    diag_ratio = qu_diag / rois_diag
    return torch.cat([cx.view(-1, 1), cy.view(-1, 1), diag_ratio.view(-1, 1)], axis=1)


# --------------------------------------------------------
# Fast R-CNN
# Copyright (c) 2015 Microsoft
# Licensed under The MIT License [see LICENSE for details]
# Written by Ross Girshick
# --------------------------------------------------------
def nms(dets, thresh):
    """ Non-maximum suppression """
    x1 = dets[:, 0]
    y1 = dets[:, 1]
    x2 = dets[:, 2]
    y2 = dets[:, 3]
    #
    scores = dets[:, 4]
    #
    areas = (x2 - x1 + 1) * (y2 - y1 + 1)
    order = scores.argsort()[::-1]
    #
    keep = []
    while order.size > 0:
        i = order[0]
        keep.append(i)
        xx1 = np.maximum(x1[i], x1[order[1:]])
        yy1 = np.maximum(y1[i], y1[order[1:]])
        xx2 = np.minimum(x2[i], x2[order[1:]])
        yy2 = np.minimum(y2[i], y2[order[1:]])
        #
        w = np.maximum(0.0, xx2 - xx1 + 1)
        h = np.maximum(0.0, yy2 - yy1 + 1)
        inter = w * h
        ovr = inter / (areas[i] + areas[order[1:]] - inter)
        #
        inds = np.where(ovr <= thresh)[0]
        order = order[inds + 1]
    return keep


def nms_torch(dets, thresh):
    """ torch version of nms """
    x1 = dets[:, 0]
    y1 = dets[:, 1]
    x2 = dets[:, 2]
    y2 = dets[:, 3]
    scores = dets[:, 4]
    areas = (x2 - x1 + 1) * (y2 - y1 + 1)
    order = torch.flip(scores.argsort(), [0])
    keep = []
    while order.size()[0] > 0:
        i = order[0]
        keep.append(i)
        xx1 = torch.max(x1[i], x1[order[1:]])
        yy1 = torch.max(y1[i], y1[order[1:]])
        xx2 = torch.min(x2[i], x2[order[1:]])
        yy2 = torch.min(y2[i], y2[order[1:]])
        #
        w = torch.max(torch.Tensor([0.0]).cuda(), xx2 - xx1 + 1)
        h = torch.max(torch.Tensor([0.0]).cuda(), yy2 - yy1 + 1)
        inter = w * h
        ovr = inter / (areas[i] + areas[order[1:]] - inter)
        inds = torch.where(ovr <= thresh)[0]
        order = order[inds + 1]
    return keep


def get_retrievals(nn_idx, nn_dist, info_vec, qids, cfg):
    """ Generate retrieval vector """
    retrievals = []
    for qid in qids:
        retrievals.append(-1 * np.ones([nn_idx.shape[1], 7]))
    for qid in qids:
        # - find reference distance for similarity conversion
        sigma = 1.0
        nn_dist_tmp = nn_dist[qid, nn_idx[qid, :] != -1]
        dist_ref = nn_dist_tmp[512] if (nn_dist_tmp.shape[0] > 512) else nn_dist_tmp[-1]
        for i, (idx_tmp, dist_tmp) in enumerate(zip(nn_idx[qid, :], nn_dist[qid, :])):
            if idx_tmp == -1:
                continue
            # convert distance to similarity
            nn_sim = np.exp(- dist_tmp**2 / (sigma**2*dist_ref**2))
            # - retrievals[qi]: image_id, bbs_ret, sim  (ordered by distance)
            retrievals[qid][i, :] = np.array([info_vec[idx_tmp, 1],
                                              info_vec[idx_tmp, 2] / cfg.RET.INFOVEC.BBSSCALE,
                                              info_vec[idx_tmp, 3] / cfg.RET.INFOVEC.BBSSCALE,
                                              info_vec[idx_tmp, 4] / cfg.RET.INFOVEC.BBSSCALE,
                                              info_vec[idx_tmp, 5] / cfg.RET.INFOVEC.BBSSCALE,
                                              nn_sim,
                                              idx_tmp])
    return retrievals


def adjust_discprop(cfg, dataset):
    """ Adjust number of maximal proposals per image """
    cfg.RET.DISCPROP.MAX = cfg.RET.DISCPROP.MAX - int(len(dataset['images_ret']) / 20000) * cfg.RET.DISCPROP.DECREASE


def get_query_from_retrieval(retrievals_ret_r, info_vec_qu, dataset, cfg):
    max_sw = 100
    num_images = np.unique([r[0] for sub in retrievals_ret_r for r in sub]).shape[0]
    info_vec = np.zeros([max_sw*num_images, 8+4+1], dtype=np.float64)  # zeros -> labels default
    ct = 0
    imgid_list, quid_list = [], []
    for qi, ret_qi in enumerate(retrievals_ret_r):
        for ri, ret in enumerate(ret_qi):
            img_id = int(ret[0])
            img_size = dataset['imagesizes'][img_id]
            ratio = cfg.RET.IMG.MINSIZE / np.min(img_size)
            img_size_pad = dataset['imagesizes_pad'][img_id]
            quid_list.append(qi)
            if img_id not in imgid_list:
                imgid_list.append(img_id)
            info_vec[ct, 0] = qi
            info_vec[ct, 1] = img_id
            info_vec[ct, 2:6] = np.array([ret[1]*img_size_pad[1]*ratio,
                                          ret[2]*img_size_pad[0]*ratio,
                                          ret[3]*img_size_pad[1]*ratio,
                                          ret[4]*img_size_pad[0]*ratio])
            info_vec[ct, 6] = 0
            info_vec[ct, 7] = info_vec_qu[qi, 7]
            info_vec[ct, 8:12] = np.array(ret[1:5])
            ct += 1

    info_vec = info_vec[0:ct, :]
    imgid_list.sort()

    query_data = dict()
    query_data['info_vec'] = info_vec
    query_data['img_ids'] = imgid_list
    query_data['qu_ids'] = np.array(quid_list).astype(np.int)
    return query_data


def concat_query_data(query_data, query_data_ret):
    query_data_res = {'info_vec': [], 'img_ids': [], 'qu_ids': []}
    query_data_res['info_vec'] = np.concatenate([query_data['info_vec'], query_data_ret['info_vec']])
    query_data_res['qu_ids'] = np.concatenate([query_data['qu_ids'], query_data_ret['qu_ids']])
    query_data_res['img_ids'] = np.unique(np.concatenate([query_data['img_ids'],
                                                          query_data_ret['img_ids']])).astype(np.int)
    return query_data_res


def mean_aggregate(features, ids, normalize=True):
    """ Feature aggregation """
    from sklearn.preprocessing import normalize
    ids_unique = np.unique(ids)
    features_res = np.zeros([max(ids_unique)+1, features.shape[1]])
    for id in ids_unique:
        features_res[id, :] = np.mean(features[ids == id, :], axis=0)
    if normalize:
        features_res = normalize(features_res, axis=1)
    return features_res


def index_filter_neg(nn_dist, nn_idx, img_neg, info_vec):
    """ Filter incorrect retrievals """
    if img_neg:
        for qi in range(nn_idx.shape[0]):
            idx_rem = np.where(np.isin(info_vec[nn_idx[qi, :], 1], img_neg[qi]))[0]
            np.unique(info_vec[nn_idx[qi, idx_rem], 1])
            nn_idx[qi, idx_rem] = -1
            nn_dist[qi, idx_rem] = np.max(nn_dist[qi, :]) + 0.001


def index_filter_pos(nn_dist, nn_idx, info_vec, info_vec_qu_ret, cfg):
    """ Filter correct retrievals """
    for qi in range(nn_idx.shape[0]):
        info_vec_qu_ret_tmp = info_vec_qu_ret[np.where(info_vec_qu_ret[:, 0] == qi)[0], :]
        for vec in info_vec_qu_ret_tmp:
            img = vec[1]
            idx_tmp = np.where(np.isin(info_vec[nn_idx[qi, :], 1], img))[0]
            rem_x1f = info_vec[nn_idx[qi, idx_tmp], 2] >= (vec[2] - 0.5 * (vec[4] - vec[2]))
            rem_y1f = info_vec[nn_idx[qi, idx_tmp], 3] >= (vec[3] - 0.5 * (vec[5] - vec[3]))
            rem_x2f = info_vec[nn_idx[qi, idx_tmp], 4] <= (vec[4] + 0.5 * (vec[4] - vec[2]))
            rem_y2f = info_vec[nn_idx[qi, idx_tmp], 5] <= (vec[5] + 0.5 * (vec[5] - vec[3]))
            idx_rem = np.where(np.invert(rem_x1f * rem_y1f * rem_x2f * rem_y2f))[0]
            nn_idx[qi, idx_tmp[idx_rem]] = -1
            nn_dist[qi, idx_tmp[idx_rem]] = np.max(nn_dist[qi, :]) + 0.001
        idx_sort = np.argsort(nn_dist[qi, :])
        nn_dist[qi, :] = nn_dist[qi, idx_sort]
        nn_idx[qi, :] = nn_idx[qi, idx_sort]


def normalize_dist(nn_dist):
    """ Normalize retrieval distance """
    nn_dist = - (nn_dist - 2) / 2.
    nn_dist = np.max(nn_dist[:]) - nn_dist
    return nn_dist

def convert_images(img_path, image_file_formats):
    """ convert all images to jpg format """
    for f in os.listdir(img_path):
        if f.endswith('.jpg'):
            continue
        elif f.lower().endswith(tuple(image_file_formats)):
            os.system(f'convert {f} {osp.splitext(f)[0]}.jpg')


def get_query_data_from_get(gt_boxes, dataset, cfg):

    # - include_padding
    for i, box in gt_boxes.iterrows():
        img_size = box['img_size']
        img_pad_org = float(cfg.RET.IMG.PADDING) / float(cfg.RET.IMG.MINSIZE) * float(np.min(img_size[:2]))
        img_size = [s + 2 * img_pad_org for s in img_size]
        bbs = [b + img_pad_org for b in box['bbs']]
        gt_boxes.at[i, 'bbs'] = bbs
        gt_boxes.at[i, 'img_size'] = img_size

    max_sw = 100
    num_images = len(gt_boxes)
    info_vec = np.zeros([max_sw*num_images, 8+4], dtype=np.float64)  # zeros -> labels default
    info_vec_imgrange = np.zeros([len(dataset['imagelist']), 2], dtype=np.float64)

    ct = 0
    imgid_list = []
    for img_id in np.unique(gt_boxes['img_id']):
        gt_boxes_tmp = gt_boxes[gt_boxes.img_id == img_id]
        img_size_pad = dataset['imagesizes_pad'][img_id]
        img_size = dataset['imagesizes'][img_id]
        ratio = cfg.RET.IMG.MINSIZE / np.min(img_size)
        if gt_boxes_tmp.shape[0] > 0:
            if img_id not in imgid_list:
                imgid_list.append(img_id)
            info_vec_imgrange[img_id, 0] = ct
            for ii, row in gt_boxes_tmp.iterrows():
                bbs_gt = row['bbs']
                # - append complete image
                info_vec[ct, 0] = row['qu_id']
                info_vec[ct, 1] = row['img_id']
                info_vec[ct, 2:6] = np.array([bbs_gt[0]*ratio,
                                              bbs_gt[1]*ratio,
                                              bbs_gt[2]*ratio,
                                              bbs_gt[3]*ratio])
                info_vec[ct, 6] = 0
                info_vec[ct, 7] = -1
                info_vec[ct, 8:12] = np.array([bbs_gt[0]/img_size_pad[1],
                                               bbs_gt[1]/img_size_pad[0],
                                               bbs_gt[2]/img_size_pad[1],
                                               bbs_gt[3]/img_size_pad[0]])
                ct += 1
            info_vec_imgrange[img_id, 1] = ct

    # - remove dummy
    info_vec = info_vec[0:ct, :]
    imgid_list.sort()
    # output datat
    query_data = dict()
    query_data['info_vec'] = info_vec
    query_data['img_ids'] = imgid_list
    query_data['info_vec_img'] = []
    query_data['qu_ids'] = [0] * info_vec.shape[0]

    return query_data


def get_query_data(search_input, image_dict, dataset, cfg):

    # - search box
    gt_boxes = {'bbs_rel': [], 'bbs': [], 'img_size': [], 'img_name': [], 'img_id': [], 'qu_id': []}
    for qi, bbs_rel in enumerate(search_input['boxes']):
        img_name = image_dict[search_input['image']]
        img_id = dataset['imagelist'].index(img_name)
        img_size = list(dataset['imagesizes'][img_id])
        bbs_rel = [k / 100. for k in bbs_rel]
        bbs = [bbs_rel[0]*img_size[1],
               bbs_rel[1]*img_size[0],
               bbs_rel[2]*img_size[1],
               bbs_rel[3]*img_size[0]]
        # - save to dictionary
        gt_boxes['bbs_rel'].append(bbs_rel)
        gt_boxes['bbs'].append(bbs)
        gt_boxes['img_size'].append(img_size)
        gt_boxes['img_name'].append(img_name)
        gt_boxes['img_id'].append(img_id)
        gt_boxes['qu_id'].append(qi)
    gt_boxes = pd.DataFrame.from_dict(gt_boxes)
    query_data = get_query_data_from_get(gt_boxes, dataset, cfg)

    # - pos box
    gt_boxes = {'bbs_rel': [], 'bbs': [], 'img_size': [], 'img_name': [], 'img_id': [], 'qu_id': []}
    num_pos = len(search_input['positives'])
    for i in range(num_pos):
        img_name = image_dict[int(search_input['positives'][i]['image_id'])]
        img_id = dataset['imagelist'].index(img_name)
        img_size = list(dataset['imagesizes'][img_id])
        # - remove duplicate positives
        if img_id in gt_boxes['img_id']:
            continue
        for qi, bbs_rel in enumerate(ast.literal_eval(search_input['positives'][i]['refined_searchbox'])):
            bbs_rel = [k / 100. for k in bbs_rel]
            bbs = [bbs_rel[0]*img_size[1],
                   bbs_rel[1]*img_size[0],
                   bbs_rel[2]*img_size[1],
                   bbs_rel[3]*img_size[0]]
            # - save to dictionary
            gt_boxes['bbs_rel'].append(bbs_rel)
            gt_boxes['bbs'].append(bbs)
            gt_boxes['img_size'].append(img_size)
            gt_boxes['img_name'].append(img_name)
            gt_boxes['img_id'].append(img_id)
            gt_boxes['qu_id'].append(qi)
    gt_boxes = pd.DataFrame.from_dict(gt_boxes)
    query_data_pos = get_query_data_from_get(gt_boxes, dataset, cfg)

    # - neg box
    gt_boxes = {'bbs_rel': [], 'bbs': [], 'img_size': [], 'img_name': [], 'img_id': [], 'qu_id': []}
    num_neg = len(search_input['negatives'])
    for i in range(num_neg):
        img_name = image_dict[int(search_input['negatives'][i]['image_id'])]
        img_id = dataset['imagelist'].index(img_name)
        img_size = list(dataset['imagesizes'][img_id])
        for qi, bbs_rel in enumerate(ast.literal_eval(search_input['negatives'][i]['refined_searchbox'])):
            bbs_rel = [k / 100. for k in bbs_rel]
            bbs = [bbs_rel[0]*img_size[1],
                   bbs_rel[1]*img_size[0],
                   bbs_rel[2]*img_size[1],
                   bbs_rel[3]*img_size[0]]
            # - save to dictionary
            gt_boxes['bbs_rel'].append(bbs_rel)
            gt_boxes['bbs'].append(bbs)
            gt_boxes['img_size'].append(img_size)
            gt_boxes['img_name'].append(img_name)
            gt_boxes['img_id'].append(img_id)
            gt_boxes['qu_id'].append(qi)
    gt_boxes = pd.DataFrame.from_dict(gt_boxes)
    query_data_neg = get_query_data_from_get(gt_boxes, dataset, cfg)

    return query_data, query_data_pos, query_data_neg
