import numpy as np
import itertools


def bbs2pts(bbs):
    pts = np.concatenate([(bbs[:, 0]+(bbs[:, 2]-bbs[:, 0])/2.).reshape(-1, 1),
                          (bbs[:, 1]+(bbs[:, 3]-bbs[:, 1])/2.).reshape(-1, 1)], axis=1)
    return pts


def bbs2diag(bbs):
    lx, ly = bbs[:, 2] - bbs[:, 0], bbs[:, 3] - bbs[:, 1]
    diag = np.sqrt(lx**2 + ly**2)
    return diag


def retrieval_geometry(bbs_qu, img_size_qu, ret_img, img_sizes, ret_bbs, ret_score, ret_idx, cfg):

    # - get query information & geometric relations
    num_qu = bbs_qu.shape[0]

    # - all retrieved images
    all_images_ret = list(set([item for sublist in ret_img for item in sublist]))

    bbs_single = [[] for i in range(len(all_images_ret))]
    img_single = [[] for i in range(len(all_images_ret))]
    score_single = [[] for i in range(len(all_images_ret))]
    edge_angle_diff = [[] for i in range(len(all_images_ret))]
    edge_dist_diff = [[] for i in range(len(all_images_ret))]
    node_feat_diff = [[] for i in range(len(all_images_ret))]
    num_edges = [[] for i in range(len(all_images_ret))]
    score_context = [[] for i in range(len(all_images_ret))]
    idx_single = [[] for i in range(len(all_images_ret))]

    ret_score_flatten = [item for sub in ret_score for item in sub]

    if (cfg.RET.CONTEXT.MODE.lower() == 'geom') & (num_qu > 1):
        pts_qu = bbs2pts(np.array(bbs_qu))  # - center of query parts
        idx_comb = np.asarray(list(itertools.combinations(range(num_qu), 2)))  # - all edge combinations between parts
        delta_qu = pts_qu[idx_comb[:, 1], :] - pts_qu[idx_comb[:, 0], :]  # - all pairwise connections
        dist_qu = np.sqrt(np.sum(delta_qu**2, axis=1))  # - all pairwise distances

    # - loop over all retrieved images
    for i, img_name in enumerate(all_images_ret):

        for ii in range(len(ret_img)):
            if img_name not in ret_img[ii]:
                ret_img[ii].append(img_name)
                ret_bbs[ii].append(np.asarray([np.nan, np.nan, np.nan, np.nan]))
                ret_score[ii].append(np.nanmax(ret_score_flatten) + 2 * np.nanstd(ret_score_flatten))
                ret_idx[ii].append(-1)

        # - get all patch combinations forming query constellation (num_cons, num_patches, bbs)
        bbs_single[i] = np.array(list(itertools.product(
            *[[ret_bbs[x][y] for y in np.where(np.asarray(ret_img[x]) == img_name)[0]] for x in range(len(ret_img))])))

        # - (num_cons, num_patches)
        score_single[i] = np.array(list(itertools.product(
            *[[ret_score[x][y] for y in np.where(np.asarray(ret_img[x]) == img_name)[0]] for x in range(len(ret_img))])))
        idx_single[i] = np.array(list(itertools.product(
            *[[ret_idx[x][y] for y in np.where(np.asarray(ret_img[x]) == img_name)[0]] for x in range(len(ret_img))])))
        num_ret = bbs_single[i].shape[0]  # - number of retrieval constellations for image
        img_single[i] = img_name * np.ones([num_ret]).astype(np.int)

        # - get context score for possible constellations within image
        if cfg.RET.CONTEXT.MODE.lower() == 'and':
            score_context[i] = np.mean(score_single[i], axis=1)

        elif cfg.RET.CONTEXT.MODE.lower() == 'or':
           score_context[i] = np.max(score_single[i], axis=1)

        elif cfg.RET.CONTEXT.MODE.lower() == 'geom':
            if num_qu <= 1:
               score_context[i] = np.mean(score_single[i], axis=1)
            else:
                # - ret image information
               delta_ret = np.array([bbs2pts(np.asarray(bbs_single[i][ii]))[idx_comb[:, 1], :] -
                                     bbs2pts(np.asarray(bbs_single[i][ii]))[idx_comb[:, 0], :] for ii in range(num_ret)])
               dist_ret = np.sqrt(np.sum(delta_ret**2, axis=2))
               diag_ret = np.array([(bbs2diag(np.array(bbs_single[i][ii])[idx_comb[:, 0]])
                                     + bbs2diag(np.array(bbs_single[i][ii])[idx_comb[:, 1]]))
                                     / 2. for ii in range(num_ret)])  # - average patch diagonal
               # - number of edges
               num_edges[i] = np.sum(~np.isnan(dist_ret), axis=1)
               # - angle diff
               edge_angle_diff[i] = np.arccos(np.sum(np.multiply(delta_qu, delta_ret), axis=2)
                                              / (np.multiply(dist_qu, dist_ret) + 1e-12)) / np.pi
               # - distance diff
               img_diag_qu = np.sqrt(np.sum(img_size_qu ** 2))  # diagonal of query image (normalization)
               img_diag_ret = np.sqrt(np.sum(img_sizes[img_name] ** 2))  # diagonal of retrieval image (normalization)
               edge_dist_diff[i] = np.abs(dist_qu / img_diag_qu - dist_ret / img_diag_ret)
               # - feature assignment
               node_feat_diff[i] = score_single[i]

    if cfg.RET.CONTEXT.MODE.lower() == 'geom':
        if num_qu > 1:
            # --- Parameter
            sigma_angle, sigma_dist, sigma_feat = 0.75, 0.75, 0.75
            lambda_feat_ass, lambda_dist, lambda_angle = 1., 1., 1.

            score_angle_energy = len(all_images_ret) * [[]]
            score_dist_energy = len(all_images_ret) * [[]]
            score_feat_energy = len(all_images_ret) * [[]]

            edge_dist_diff_ref = np.nanmax(np.concatenate([edge_dist_diff[i] for i in range(len(edge_dist_diff))], axis=0))
            node_feat_diff_ref = np.max(np.concatenate([node_feat_diff[i][node_feat_diff[i] != 1e12] for i in range(len(edge_dist_diff))]))

            for i, img_name in enumerate(all_images_ret):
                # - set to ref
                edge_angle_diff[i][np.isnan(edge_angle_diff[i])] = 1.0  # - if missing
                edge_dist_diff[i][np.isnan(edge_dist_diff[i])] = edge_dist_diff_ref  # - if missing
                node_feat_diff[i][np.isnan(node_feat_diff[i])] = node_feat_diff_ref  # - if missing
                # - unary: feature distance
                node_feat_diff[i][np.isnan(node_feat_diff[i])] = np.nanmax(node_feat_diff[i]) + 5 * np.nanstd(node_feat_diff[i])
                score_feat_energy[i] = np.sum(np.exp((node_feat_diff[i] / node_feat_diff_ref)**2 / (sigma_feat ** 2)) - 1, axis=1)
                # - edge: angle energy
                if num_edges[i] != 0:
                    score_angle_energy[i] = np.sum(np.exp(edge_angle_diff[i] ** 2 / (sigma_angle ** 2)) - 1, axis=1) / num_edges[i]
                else:
                    score_angle_energy[i] = np.nanmax(edge_angle_diff[i]) + 5 * np.nanstd(edge_angle_diff[i])
                # - edge: distance energy
                edge_dist_diff[i][np.isnan(edge_dist_diff[i])] = np.nanmax(edge_dist_diff[i]) + 5 * np.nanstd(edge_dist_diff[i])
                edge_dist_diff_norm = edge_dist_diff[i] / edge_dist_diff_ref
                if num_edges[i] != 0:
                    score_dist_energy[i] = np.sum(np.exp(edge_dist_diff_norm ** 2 / sigma_dist ** 2) - 1, axis=1) / num_edges[i]
                else:
                    score_dist_energy[i] = np.nanmax(edge_dist_diff[i]) + 5 * np.nanstd(edge_dist_diff[i])

                weights = cfg.RET.CONTEXT.WEIGHTS
                score_context[i] = weights[0] * lambda_feat_ass * score_feat_energy[i] \
                                   + weights[2] * lambda_dist * score_dist_energy[i] \
                                   + weights[1] * lambda_angle * score_angle_energy[i]

    bbs_return = np.concatenate(bbs_single)
    idx_return = np.concatenate(idx_single).astype(np.int)
    score_single_return = np.concatenate(score_single)
    score_context_return = np.concatenate(score_context)
    img_single_return = np.concatenate(img_single)

    # - set score to 1e12
    score_context_return[np.where(np.isnan(score_context_return))] = 1e12

    # - sort
    score_context_return = score_context_return

    # - sort based on energy
    idx_sort = np.argsort(score_context_return)
    idx_return = idx_return[idx_sort]
    bbs_return = bbs_return[idx_sort]
    score_single_return = score_single_return[idx_sort]
    score_context_return = score_context_return[idx_sort]
    img_single_return = img_single_return[idx_sort]

    # - filter only one hit per image
    unique_values, unique_index = np.unique(img_single_return, return_index=True)
    unique_index = np.sort(unique_index)  # - keep original ordering
    idx_return = idx_return[unique_index, :]
    bbs_return = bbs_return[unique_index, :, :]
    score_single_return = score_single_return[unique_index, :]
    score_context_return = score_context_return[unique_index]
    img_single_return = img_single_return[unique_index]

    # convert to list
    bbs_return = bbs_return.tolist()
    score_single_return = score_single_return.tolist()
    score_context_return = score_context_return.tolist()
    img_single_return = img_single_return.tolist()

    num_bbs = np.sum(~np.isnan(score_single_return), axis=1)

    return img_single_return, num_bbs, bbs_return, score_single_return, score_context_return, idx_return
