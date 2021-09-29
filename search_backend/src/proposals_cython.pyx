from tqdm import tqdm
import numpy as np

from src.utils import loadGT


def extract_sliding_window(dataset, cfg, include_gt='exclude'):
    """ Extract local patches in a sliding window manner"""

    assert(include_gt in ['exclude', 'only', 'include'])

    max_sw = 6000  # maximal number of patches per image
    num_images = len(dataset['images_ret'])

    if include_gt in ['only', 'include']:
        # - whether to include gt bounding boxes
        gt_boxes = loadGT(dataset['anno_file_ret'], cfg, include_padding=True)

    # - info_vec (all patches): 0: image_id, 1: proposal id, 2-5: bbs, 6: scale, 7: label id, 8-12: bbs_rel
    cdef double[:, :] info_vec = np.zeros((max_sw*num_images, 12), dtype=np.float64)
    # - info_vec_img: (holistic images): 0: image_id, 1: proposal id, 2-5: bbs, 6: scale, 7: label id, 8-12: bbs_rel
    cdef double[:, :] info_vec_img = np.zeros((num_images, 12), dtype=np.float64)
    # - info_vec_imgarange: proposal range for image with image id
    cdef double[:, :] info_vec_imgrange = np.zeros((len(dataset['imagelist']), 2), dtype=np.float64)

    if not cfg.RET.ROI.PARAMETERS:
        # size_ratio, stride_ratio, number of scales per octave, number of octaves, number of scales per octave for stride
        roi_parameters = [2., 50., 2., 1.59, 3.]
    else:
        roi_parameters = cfg.RET.ROI.PARAMETERS
        assert(len(roi_parameters) == 5), 'Wrong number of roi parameters: %d' % (len(roi_parameters))

    # - sliding window parameter
    w_scale_num = int(roi_parameters[2] * roi_parameters[4])
    w_scale_factor = np.power(roi_parameters[2], 1./2)  # scaling factor of window size
    w_scales = [w_scale_factor**i for i in range(w_scale_num)]  # window size scales
    w_scale_factor_stride = np.power(roi_parameters[3], 1./2)  # scaling factor of stride
    w_scales_stride = [w_scale_factor_stride**i for i in range(w_scale_num)]  # stride size scales

    cdef int sc, x1, x2, y1, y2, ct, imgid
    cdef float w_scale, w_scale_stride
    cdef long[:] imgsize_pad = np.zeros(2, dtype=np.int)
    cdef long[:] imgsize = np.zeros(2, dtype=np.int)

    imgid_list = []
    ct = 0
    for i, imgid in tqdm(enumerate(set(dataset['images_ret']))):
        imgsize_pad = dataset['imagesizes_pad'][imgid].astype(np.int)  # - consider padded input images
        imgsize = dataset['imagesizes'][imgid]
        info_vec_imgrange[imgid, 0] = ct
        if include_gt != 'only':
            if imgid not in imgid_list:
                imgid_list.append(imgid)
            # - get image proposals in a sliding window manner
            w_size_min = int(round(max(imgsize_pad) / roi_parameters[0]))
            w_stride = int(round(max(imgsize_pad) / roi_parameters[1]))
            for sc, (w_scale, w_scale_stride) in enumerate(zip(w_scales, w_scales_stride)):
                for x1 in range(0, imgsize_pad[1], int(round(w_stride*w_scale_stride))):
                    x2 = int(x1+w_size_min*w_scale-1)
                    for y1 in range(0, imgsize_pad[0], int(round(w_stride*w_scale_stride))):
                        y2 = int(y1+w_size_min*w_scale-1)
                        if (x2 < imgsize_pad[1]) & (y2 < imgsize_pad[0]) & (x1 < x2) & (y1 < y2):
                            info_vec[ct, 0] = imgid
                            info_vec[ct, 1] = ct
                            info_vec[ct, 2] = x1
                            info_vec[ct, 3] = y1
                            info_vec[ct, 4] = x2
                            info_vec[ct, 5] = y2
                            info_vec[ct, 6] = sc
                            info_vec[ct, 7] = 0  # no label available
                            info_vec[ct, 8] =  float(x1)/imgsize_pad[1]
                            info_vec[ct, 9] =  float(y1)/imgsize_pad[0]
                            info_vec[ct, 10] = float(x2)/imgsize_pad[1]
                            info_vec[ct, 11] = float(y2)/imgsize_pad[0]
                            ct += 1

            # - append whole image
            info_vec[ct, 0] = imgid
            info_vec[ct, 1] = ct
            info_vec[ct, 2] = 0
            info_vec[ct, 3] = 0
            info_vec[ct, 4] = imgsize_pad[1]
            info_vec[ct, 5] = imgsize_pad[0]
            info_vec[ct, 6] = len(w_scales) + 1  # labels starting from 1
            info_vec[ct, 7] = 0  # no label available
            info_vec[ct, 8] = float(0)
            info_vec[ct, 9] = float(0)
            info_vec[ct, 10] = float(1)
            info_vec[ct, 11] = float(1)
            ct += 1

        if include_gt in ['only', 'include']:
            # - include gt boxes
            for iii, row in gt_boxes[gt_boxes.img_id == imgid].iterrows():
                if imgid not in imgid_list:
                    imgid_list.append(imgid)
                bbs_gt = row['bbs']
                info_vec[ct, 0] = imgid
                info_vec[ct, 1] = ct
                info_vec[ct, 2] = bbs_gt[0]
                info_vec[ct, 3] = bbs_gt[1]
                info_vec[ct, 4] = bbs_gt[2]
                info_vec[ct, 5] = bbs_gt[3]
                info_vec[ct, 6] = len(w_scales) + 1  # labels starting from 1
                info_vec[ct, 7] = row['label']
                info_vec[ct, 8] =  float(bbs_gt[0])/imgsize_pad[1]
                info_vec[ct, 9] =  float(bbs_gt[1])/imgsize_pad[0]
                info_vec[ct, 10] = float(bbs_gt[2])/imgsize_pad[1]
                info_vec[ct, 11] = float(bbs_gt[3])/imgsize_pad[0]
                ct += 1

        # - info_vec_imgarange: proposal range for image imgid
        info_vec_imgrange[imgid, 1] = ct

        # - info_vec_img: just complete images
        info_vec_img[i, 0] = imgid
        info_vec_img[i, 1] = ct
        info_vec_img[i, 2] = 0
        info_vec_img[i, 3] = 0
        info_vec_img[i, 4] = imgsize[1]*cfg.RET.INFOVEC.BBSSCALE
        info_vec_img[i, 5] = imgsize[0]*cfg.RET.INFOVEC.BBSSCALE
        info_vec_img[i, 6] = 0
        info_vec_img[i, 7] = 0  # no label available
        info_vec_img[i, 8] = 0
        info_vec_img[i, 9] = 0
        info_vec_img[i, 10] = 1.0
        info_vec_img[i, 11] = 1.0

    # - remove dummpy
    info_vec = info_vec[0:ct, :]
    imgid_list.sort()

    # output datat
    prop_data = dict()
    prop_data['info_vec'] = info_vec
    prop_data['img_ids'] = imgid_list
    prop_data['img_range'] = info_vec_imgrange
    prop_data['info_vec_img'] = info_vec_img

    return prop_data






