import numpy as np
from collections import defaultdict
import cython
from libc.math cimport exp as c_exp
from libc.math cimport sqrt as c_sqrt
import torch
from torch.nn import functional as F

from src import utils

#cython: boundscheck=False, wraparound=False, nonecheck=False

def vote(nn_idx, nn_dist, info_vec, info_vec_imgrange, info_vec_qu, nn_idx_v, nn_dist_v, shift_v, shift_qu, num_votes_qu, dataset, cfg, vote_name='', qu_range=0):
    """ Local patch descriptor voting"""

    retrievals = []
    # - iteration over all queries
    qu_range = qu_range if qu_range else range(nn_idx.shape[0])
    cdef int qi
    for qi in qu_range:
        idx_range = list(range(np.sum(num_votes_qu[0:(qi+1)]), np.sum(num_votes_qu[0:(qi+2)])))
        nn_idx_qi, nn_dist_qi, nn_idx_v_qi, nn_dist_v_qi, retrievals_qi = vote_qi(nn_idx[qi, :],
                                                                                  nn_dist[qi, :],
                                                                                  info_vec,
                                                                                  info_vec_imgrange,
                                                                                  info_vec_qu[qi, :],
                                                                                  nn_idx_v[idx_range, :],
                                                                                  nn_dist_v[idx_range, :],
                                                                                  shift_v[idx_range, :],
                                                                                  shift_qu[qi, :],
                                                                                  num_votes_qu[0:(qi+2)],
                                                                                  dataset,
                                                                                  cfg,
                                                                                  vote_name=vote_name)

        nn_idx[qi, :] = nn_idx_qi
        nn_dist[qi, :] = nn_dist_qi
        nn_idx_v[idx_range, :] = nn_idx_v_qi
        nn_dist_v[idx_range, :] = nn_dist_v_qi
        retrievals.append(retrievals_qi)

    return nn_idx, nn_dist, nn_idx_v, nn_dist_v, retrievals


def vote_ret(nn_idx, nn_dist, info_vec, info_vec_imgrange, info_vec_qu, info_vec_qu_ret, nn_idx_v, nn_dist_v, shift_v_ret, shift_qu, num_votes_qu_ret, dataset, cfg, vote_name='', qu_range=0):

    # - iteration over all queries
    retrievals = []
    qu_range = qu_range if qu_range else range(nn_idx.shape[0])
    cdef int qi
    for qi in qu_range:
        idx_qi_range = np.where(info_vec_qu_ret[:, 0] == qi)[0]
        idx_range = np.concatenate([list(range(np.sum(num_votes_qu_ret[0:(qi_tmp+1)]),
                                               np.sum(num_votes_qu_ret[0:(qi_tmp+2)]))) for qi_tmp in idx_qi_range]).astype(np.int32)

        nn_idx_qi, nn_dist_qi, nn_idx_v_qi, nn_dist_v_qi, retrievals_qi = vote_qi(nn_idx[qi, :],
                                                                                  nn_dist[qi, :],
                                                                                  info_vec,
                                                                                  info_vec_imgrange,
                                                                                  info_vec_qu[qi, :],
                                                                                  nn_idx_v[idx_range, :],
                                                                                  nn_dist_v[idx_range, :],
                                                                                  shift_v_ret[idx_range, :],
                                                                                  shift_qu[qi, :],
                                                                                  num_votes_qu_ret[0:(qi+2)],
                                                                                  dataset,
                                                                                  cfg,
                                                                                  vote_name=vote_name)
        nn_idx[qi, :] = nn_idx_qi
        nn_dist[qi, :] = nn_dist_qi
        nn_idx_v[idx_range, :] = nn_idx_v_qi
        nn_dist_v[idx_range, :] = nn_dist_v_qi
        retrievals.append(retrievals_qi)

    return nn_idx, nn_dist, nn_idx_v, nn_dist_v, retrievals


@cython.cdivision(True)
def vote_qi(nn_idx_qi, nn_dist_qi, info_vec, info_vec_imgrange, info_vec_qu_qi, nn_idx_v_qi, nn_dist_v_qi,
            shift_v_qi, shift_qu_qi, num_votes_qu_qi, dataset, cfg, vote_name=''):
    """ Local patch descriptor voting single query """

    cdef int max_imagehit = 1
    cdef float sigma = 1.0
    cdef int img, idx, ii, jj, iii, vid, nn_hit, vx, vy
    cdef float dist, prob_tmp, dist_ref, dist_ref_v, bbs_diag
    cdef double[:] bbs = np.zeros([4], dtype=np.float64)
    cpdef int[:, :] info_vec_non = info_vec
    cdef long[:] vspace_dim = np.ones([2], dtype=np.int64)
    cdef float BBSSCALE = cfg.RET.INFOVEC.BBSSCALE

    img_vote = {}
    diag_vote = {}
    img_idx = {}
    img_idx_v = {}
    img_idx_prob = {}
    img_idx_v_prob = {}
    img_prob = defaultdict(int)
    num_votes = nn_idx_v_qi.shape[0]

    # --------------------------------
    # image-level vote
    # --------------------------------

    # - query
    cpdef long[:] nn_idx_tmp = nn_idx_qi.copy()
    cpdef float[:] nn_dist_tmp = nn_dist_qi.copy()
    cpdef int[:] img_tmp = np.zeros([nn_idx_tmp.shape[0]], dtype=np.int32)
    cpdef float[:] shift_qu_qi_non = np.asarray(shift_qu_qi, dtype=np.float32)
    cpdef float[:] shift_qu_tmp = np.zeros([2], dtype=np.float32)
    cpdef float[:, :] shift_v_qi_non = np.asarray(shift_v_qi, dtype=np.float32)
    cpdef float[:] shift_v_tmp = np.zeros([2], dtype=np.float32)

    for i in range(img_tmp.shape[0]):
        img_tmp[i] = info_vec_non[nn_idx_tmp[i], 1]
    dist_ref = nn_dist_tmp[512] if (nn_dist_tmp.shape[0] > 512) else nn_dist_tmp[-1]

    # - voting of query region retrievals
    for ii in range(nn_idx_tmp.shape[0]):
        idx = nn_idx_tmp[ii]
        if idx == -1:
            continue
        img = img_tmp[ii]
        dist = nn_dist_tmp[ii]
        if img not in img_idx.keys():
            img_idx[img] = -1 * np.ones(max_imagehit).astype(np.int)
            img_idx_prob[img] = np.zeros(max_imagehit).astype(np.float)
        if img_idx[img] == -1:
            prob_tmp = c_exp(- dist**2 / (sigma**2*dist_ref**2))
            img_prob[img] += prob_tmp
            img_idx[img] = idx
            img_idx_prob[img] = prob_tmp

    # - voting of local patch retrievals
    if num_votes != 0:
        for ii, (nn_idx_v_tmp, nn_dist_v_tmp) in enumerate(zip(nn_idx_v_qi, nn_dist_v_qi)):
            dist_ref_v = nn_dist_v_tmp[512] if (nn_dist_v_tmp.shape[0] > 512) else nn_dist_v_tmp[-1]
            img_v_tmp = info_vec[nn_idx_v_tmp, 1]
            for img, idx, dist in zip(img_v_tmp, nn_idx_v_tmp, nn_dist_v_tmp):
                if idx == -1:
                    continue
                if img not in img_idx_v.keys():
                    img_idx_v[img] = -1 * np.ones([num_votes, max_imagehit], dtype=np.int)
                    img_idx_v_prob[img] = np.zeros([num_votes, max_imagehit], dtype=np.float)
                if img_idx_v[img][ii][0] == -1:
                    prob_tmp = c_exp(- dist**2 / (sigma**2*dist_ref_v**2))
                    img_prob[img] += prob_tmp
                    img_idx_v[img][ii, 0] = idx
                    img_idx_v_prob[img][ii, 0] = prob_tmp

    # - get most interesting images & filter
    img_order = [t[0] for t in sorted(img_prob.items(), key=lambda kv: kv[1], reverse=True)]
    img_scores = [t[1] for t in sorted(img_prob.items(), key=lambda kv: kv[1], reverse=True)]

    # -----------------------------
    # Localization
    # -----------------------------

    # - voting kernel
    kernel_init = np.array([[0.20, 0.30, 0.40, 0.50, 0.40, 0.30, 0.20],
                       [0.30, 0.40, 0.50, 0.75, 0.50, 0.40, 0.30],
                       [0.40, 0.50, 0.75, 0.90, 0.75, 0.50, 0.40],
                       [0.50, 0.75, 0.90, 1.00, 0.90, 0.75, 0.50],
                       [0.40, 0.50, 0.75, 0.90, 0.75, 0.50, 0.40],
                       [0.30, 0.40, 0.50, 0.75, 0.50, 0.40, 0.30],
                       [0.20, 0.30, 0.40, 0.50, 0.40, 0.30, 0.20]])
    kernel = kernel_init / np.sum(kernel_init)
    cdef int dkernel = int(np.floor(kernel_init.shape[0] / 2))

    vspace_dim_max = 100  # dimension of voting map

    first_patches = []
    first_patches_dist = []
    retrievals_qi = []
    # - loop over promising retrievals
    for iii in range(min(len(img_order), cfg.RET.VOTING.NUMRELIMAGES)):
        img = img_order[iii]
        img_score = img_scores[iii]
        img_size = dataset['imagesizes'][img]
        vspace_dim = np.asarray(dataset['imagesizes'][img] / np.max(dataset['imagesizes'][img]) * vspace_dim_max, dtype=np.int)

        # - initialize voting maps
        img_vote[img] = np.zeros([vspace_dim[0] + 2*dkernel, vspace_dim[1] + 2*dkernel], dtype=np.float32)
        diag_vote[img] = np.zeros([vspace_dim[0] + 2*dkernel, vspace_dim[1] + 2*dkernel], dtype=np.float32)

        # - aggregate query patch
        if img in img_idx.keys():
            # - hits per image
            nn_hit = img_idx[img]
            prob_hit = img_idx_prob[img]
            if nn_hit == -1:
                continue
            bbs[0] = info_vec_non[nn_hit, 2] / BBSSCALE * vspace_dim[1]
            bbs[1] = info_vec_non[nn_hit, 3] / BBSSCALE * vspace_dim[0]
            bbs[2] = info_vec_non[nn_hit, 4] / BBSSCALE * vspace_dim[1]
            bbs[3] = info_vec_non[nn_hit, 5] / BBSSCALE * vspace_dim[0]
            bbs_diag = c_sqrt((bbs[2]-bbs[0])**2 + (bbs[3]-bbs[1])**2)
            shift_qu_tmp[0] = shift_qu_qi_non[0] * bbs_diag
            shift_qu_tmp[1] = shift_qu_qi_non[1] * bbs_diag
            vx = int((bbs[2]+bbs[0]) / 2.0 + shift_qu_tmp[0])
            vx = vx + dkernel
            vy = int((bbs[3]+bbs[1]) / 2.0 + shift_qu_tmp[1])
            vy = vy + dkernel
            try:
                img_vote[img][(vy-dkernel):(vy+(dkernel+1)), (vx-dkernel):(vx+(dkernel+1))] += kernel * prob_hit
                diag_vote[img][(vy-dkernel):(vy+(dkernel+1)), (vx-dkernel):(vx+(dkernel+1))] += kernel * prob_hit * shift_qu_qi[2] * bbs_diag
            except:
                pass

        # - aggergate voting patches
        if num_votes != 0:
            if img in img_idx_v.keys():
                img_size = dataset['imagesizes'][img]
                # - iterate over voting patches
                for vid in range(img_idx_v[img].shape[0]):
                    # - iterate over hits in image
                    for nn_hit, prob_hit in zip(img_idx_v[img][vid], img_idx_v_prob[img][vid]):
                        if nn_hit == -1:
                            continue
                        bbs[0] = info_vec_non[nn_hit, 2] / BBSSCALE * vspace_dim[1]
                        bbs[1] = info_vec_non[nn_hit, 3] / BBSSCALE * vspace_dim[0]
                        bbs[2] = info_vec_non[nn_hit, 4] / BBSSCALE * vspace_dim[1]
                        bbs[3] = info_vec_non[nn_hit, 5] / BBSSCALE * vspace_dim[0]
                        bbs_diag = c_sqrt((bbs[2]-bbs[0])**2 + (bbs[3]-bbs[1])**2)
                        shift_v_tmp[0] = shift_v_qi_non[vid, 0] * bbs_diag
                        shift_v_tmp[1] = shift_v_qi_non[vid, 1] * bbs_diag
                        vx = int((bbs[2]+bbs[0]) / 2.0 + shift_v_tmp[0])
                        vx += dkernel
                        vy = int((bbs[3]+bbs[1]) / 2.0 + shift_v_tmp[1])
                        vy += dkernel
                        try:
                            img_vote[img][(vy-dkernel):(vy+(dkernel+1)), (vx-dkernel):(vx+(dkernel+1))] += kernel * prob_hit
                            diag_vote[img][(vy-dkernel):(vy+(dkernel+1)), (vx-dkernel):(vx+(dkernel+1))] += kernel * prob_hit * shift_v_qi[vid, 2] * bbs_diag
                        except:
                            pass

        # - normalization
        if iii == 0:
            max_prob_hit = np.max(img_vote[img])
        img_vote[img] /= max_prob_hit
        diag_vote[img] /= max_prob_hit

        # - convolve voting map
        conv_kernel = torch.Tensor(kernel / np.sum(kernel)).unsqueeze(0).unsqueeze(0)
        img_vote_input = torch.FloatTensor(img_vote[img]).reshape(1, 1, img_vote[img].shape[0], img_vote[img].shape[1])
        img_vote_conv = F.conv2d(img_vote_input, conv_kernel, stride=1, padding=dkernel).numpy().squeeze()

        # - determine max
        argmax_tmp = np.argmax(img_vote_conv)
        vx = int(argmax_tmp % (vspace_dim[1] + 2*dkernel))
        vy = int(argmax_tmp / (vspace_dim[1] + 2*dkernel))
        vote_max = img_vote_conv[vy, vx]
        x, y = vx - dkernel, vy - dkernel
        info_vec_tmp = info_vec[info_vec_imgrange[img][0]:(info_vec_imgrange[img][1]+1), :]
        c = utils.bbs2center(info_vec_tmp[:, 2:6] /
                             cfg.RET.INFOVEC.BBSSCALE *
                             np.array([vspace_dim[1], vspace_dim[0], vspace_dim[1], vspace_dim[0]]))

        # - mindistScale
        img_size_qu = dataset['imagesizes'][info_vec_qu_qi[1]]
        bbs_qu = info_vec_qu_qi[2:6] / cfg.RET.INFOVEC.BBSSCALE * np.array([img_size_qu[1], img_size_qu[0], img_size_qu[1], img_size_qu[0]])
        diag_vote_tmp = diag_vote[img][vy, vx] / (img_vote[img][vy, vx] + 1e-10)

        l1 = bbs_qu[2]-bbs_qu[0]
        l2 = bbs_qu[3]-bbs_qu[1]
        a = np.sqrt(diag_vote_tmp**2 / float(l1**2 + l2**2))
        l_x = l1 * a / float(vspace_dim[1])
        l_y = l2 * a / float(vspace_dim[0])
        bbs_ret = [max(x/float(vspace_dim[1])-l_x/2, 0),
                   max(y/float(vspace_dim[0])-l_y/2, 0),
                   min(x/float(vspace_dim[1])+l_x/2, 1.0),
                   min(y/float(vspace_dim[0])+l_y/2, 1.0)]

        # - for embedding
        idx_image_hit = np.where(info_vec[nn_idx_tmp, 1] == img)[0]
        if idx_image_hit.shape[0] != 0:
            id_hit = nn_idx_tmp[idx_image_hit[0]]
        else:
            l2dist = np.sqrt(np.sum(np.power(c - np.array([x, y]), 2), axis=1))
            idx_select = np.argsort(l2dist)[0:50]
            bbs_tmp = info_vec_tmp[idx_select, 2:6] / cfg.RET.INFOVEC.BBSSCALE
            id_hit = idx_select[np.argmax(utils.bbs_iou_s(bbs_ret, bbs_tmp))]
            id_hit = info_vec_tmp[id_hit, 0]

        retrievals_qi.append(np.array([img] + bbs_ret + [img_score] + [id_hit]).reshape(1, -1))

    nn_idx_qi = nn_idx_tmp
    nn_dist_qi = nn_dist_tmp
    retrievals_qi = np.concatenate(retrievals_qi, axis=0)

    return nn_idx_qi, nn_dist_qi, nn_idx_v_qi, nn_dist_v_qi, retrievals_qi

