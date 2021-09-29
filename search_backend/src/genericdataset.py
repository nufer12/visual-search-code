import os
import os.path as osp
import numpy as np
import time
from PIL import Image
import cv2
import torch
import torch.utils.data as data
import logging

from src.utils import read_gt_csv, pil_loader


class ImagesStylizationsFromList(data.Dataset):

    """ Data loader that loads images + stylizations + local patches (Based on ImagesFromList ) """

    def __init__(self, prop_data_1, images, dataset, cfg, rois_file=None, scales=[1], bbxs=None, transform=None, f_stride=16.):

        self.dataset = dataset
        self.images = images
        self.prop_data_1 = prop_data_1
        self.images_fn = [os.path.join(self.dataset['img_path'], self.dataset['imagelist'][id]) for id in images]
        self.imagesAug_fn = [os.path.join(cfg.TRANS.STYLE_PATH, self.dataset['imagelist'][id]) for id in images]
        if len(self.images_fn) == 0:
            raise(RuntimeError("Dataset contains 0 images!"))
        self.bbxs = bbxs
        self.transform = transform
        self.f_stride = f_stride
        self.loader = pil_loader
        self.scales = scales
        self.num_scales = len(scales)
        self.cfg = cfg

        # - loading global rois file
        if rois_file:
            self.rois_csv = read_gt_csv(rois_file)
            # - check if there is some overlap images <-> annotations
            num_overlap = len(set(self.rois_csv['img_name'].values) & set([image.replace('.jpg', '') for image in images]))
            assert (num_overlap > 0), 'There is no overlap between images and annotations!!!'
        else:
            self.rois_csv = None

    def __getitem__(self, index):
        path = self.images_fn[index]
        img_id = self.images[index]
        img = self.loader(path)  # range 0-255
        imsize = img.size
        im = np.array(img).astype(np.float32, copy=False)
        im_shape = im.shape
        im_size_min = np.min(im_shape[0:2])

        # - padding to capture border objects
        img_pad_org = int(self.cfg.RET.IMG.PADDING / self.cfg.RET.IMG.MINSIZE * float(im_size_min))
        im_pad = cv2.copyMakeBorder(im, img_pad_org, img_pad_org, img_pad_org, img_pad_org, cv2.BORDER_REFLECT)
        im_scales = [float(self.cfg.RET.IMG.MINSIZE + 2*self.cfg.RET.IMG.PADDING) / float(im_size_min + 2*img_pad_org) * sc for sc in self.scales]
        images = [cv2.resize(im_pad, None, None, fx=im_sc, fy=im_sc, interpolation=cv2.INTER_LINEAR) for im_sc in im_scales]
        imsizes = []
        for i, im in enumerate(images):
            img = Image.fromarray(im.astype('uint8'), 'RGB')
            if self.transform is not None:
                img = self.transform(img)
                imsize = [img.shape[1], img.shape[2]]
            # append images and image sizes
            images[i] = img
            imsizes.append(imsize)

        # - stylizations
        images_st = []
        if self.cfg.RET.STYLE_FLAG:
            imgAug_path = self.imagesAug_fn[index]
            img_id = self.images[index]
            for ii, augid in enumerate(self.cfg.RET.STYLE_IDS):
                img = self.loader(osp.splitext(imgAug_path)[0] + '_%d.png' % (augid))  # range 0-255
                im = np.array(img).astype(np.float32, copy=False)
                im_shape = im.shape
                im_size_min = np.min(im_shape[0:2])
                # - padding to capture border objects
                img_pad_org = int(self.cfg.RET.IMG.PADDING / self.cfg.RET.IMG.MINSIZE * float(im_size_min))
                im_pad = cv2.copyMakeBorder(im, img_pad_org, img_pad_org, img_pad_org, img_pad_org, cv2.BORDER_REFLECT)
                im_scales = [float(self.cfg.RET.IMG.MINSIZE + 2*self.cfg.RET.IMG.PADDING) / float(im_size_min + 2*img_pad_org) * sc for sc in self.scales]
                images_st.append([cv2.resize(im_pad, (f[1], f[0]), interpolation=cv2.INTER_LINEAR) for f in imsizes])
                for i, im in enumerate(images_st[ii]):
                    img = Image.fromarray(im.astype('uint8'), 'RGB')
                    if self.transform is not None:
                        img = self.transform(img)
                    # append images
                    images_st[ii][i] = img

        # - rois loading
        ifv1_img_range = self.prop_data_1['img_range'][img_id].astype(np.int)
        ifv1_bbsrel = self.prop_data_1['info_vec'][ifv1_img_range[0]:ifv1_img_range[1], 8:12]
        ifv1_scales = self.prop_data_1['info_vec'][ifv1_img_range[0]:ifv1_img_range[1], 6]
        rois_rel = ifv1_bbsrel
        imsize_base = imsizes[0]
        rois = ifv1_bbsrel * np.array([imsize_base[1],
                                         imsize_base[0],
                                         imsize_base[1],
                                         imsize_base[0]]).reshape(1, 4)
        scales = ifv1_scales

        # - image names
        imgids = torch.IntTensor([img_id] * len(rois))
        rois_rel = torch.Tensor(rois_rel)
        rois = torch.Tensor(rois)
        imsizes = [torch.Tensor(imsize) for imsize in imsizes]

        # - find correct scales (smallest scale with min feature dim 5 pixels)
        psize = self.cfg.RET.NETWORK.POOLING.SIZE

        if rois.shape[0] == 0:
            proposals = {}
            return images, imgids, imsizes, proposals

        mside = torch.min(torch.stack((rois[:, 2]-rois[:, 0], rois[:, 3] - rois[:, 1]), dim=0), dim=0)[0]
        mside_f = torch.mul(mside, 1/self.f_stride).unsqueeze(dim=1)
        rois_scale = torch.argmin(torch.abs(torch.mul(mside_f, torch.tensor(self.scales).unsqueeze(dim=0)) - (psize + 0.5)), dim=1)
        scales = torch.Tensor(scales)

        proposals = {'rois': rois, 'rois_rel': rois_rel, 'rois_scale': rois_scale, 'scales': scales}

        return images, images_st, imgids, imsizes, proposals, []

    def __len__(self):
        return len(self.images_fn)

    def __repr__(self):
        fmt_str = 'Dataset ' + self.__class__.__name__ + '\n'
        fmt_str += '    Number of images: {}\n'.format(self.__len__())
        fmt_str += '    Root Location: {}\n'.format(self.dataset['img_path'])
        tmp = '    Transforms (if any): '
        fmt_str += '{0}{1}\n'.format(tmp, self.transform.__repr__().replace('\n', '\n' + ' ' * len(tmp)))
        return fmt_str


class ImagesStylizationsQueriesFromList(data.Dataset):
    """ Data loader that loads images + stylizations + local patches + queries (Based on ImagesFromList ) """

    def __init__(self, prop_data_1, images, dataset, cfg, prop_data_2=[], rois_file=None, rois_path=None, scales=[1], bbxs=None, transform=None, f_stride=16.):

        self.dataset = dataset
        self.prop_data_1 = prop_data_1
        self.prop_data_2 = prop_data_2
        self.images = np.unique(prop_data_1['info_vec'][:, 1].astype('int'))
        self.images_fn = [os.path.join(self.dataset['img_path'], self.dataset['imagelist'][id]) for id in self.images]
        if len(self.images_fn) == 0:
            raise(RuntimeError("Dataset contains 0 images!"))
        self.imagesAug_fn = [os.path.join(cfg.TRANS.STYLE_PATH, self.dataset['imagelist'][id]) for id in self.images]
        self.bbxs = bbxs
        self.transform = transform
        self.f_stride = f_stride
        self.loader = pil_loader
        self.scales = scales
        self.num_scales = len(scales)
        self.cfg = cfg

        # - loading global rois file
        if rois_file:
            t1 = time.time()
            self.rois_csv = read_gt_csv(rois_file)
            # - check if there is some overlap images <-> annotations
            num_overlap = len(set(self.rois_csv['img_id'].values) & set(images))
            assert (num_overlap > 0), 'There is no overlap between images and annotations!!!'
        else:
            self.rois_csv = None

        # - path to local rois files
        if rois_path:
            self.rois_path = rois_path
        else:
            self.rois_path = None

    def __getitem__(self, index):
        path = self.images_fn[index]
        img_id = self.images[index]
        img = self.loader(path)  # range 0-255
        imsize = img.size
        if self.bbxs:
            img = img.crop(self.bbxs[index])

        im = np.array(img).astype(np.float32, copy=False)
        im_shape = im.shape
        im_size_min = np.min(im_shape[0:2])

        # - padding to capture border objects
        img_pad_org = int(self.cfg.RET.IMG.PADDING / (self.cfg.RET.IMG.MINSIZE) * float(im_size_min))
        im_pad = cv2.copyMakeBorder(im, img_pad_org, img_pad_org, img_pad_org, img_pad_org, cv2.BORDER_REFLECT)
        im_scales = [float(self.cfg.RET.IMG.MINSIZE + 2*self.cfg.RET.IMG.PADDING) / float(im_size_min + 2*img_pad_org) * sc for sc in self.scales]
        images = [cv2.resize(im_pad, None, None, fx=im_sc, fy=im_sc, interpolation=cv2.INTER_LINEAR) for im_sc in im_scales]
        imsizes = []
        for i, im in enumerate(images):
            img = Image.fromarray(im.astype('uint8'), 'RGB')
            if self.transform is not None:
                img = self.transform(img)
                imsize = [img.shape[1], img.shape[2]]
            # append images and image sizes
            images[i] = img
            imsizes.append(imsize)

        # stylizations
        images_st = []
        if self.cfg.RET.STYLE_FLAG:
            imgAug_path = self.imagesAug_fn[index]
            img_id = self.images[index]
            for ii, augid in enumerate(self.cfg.RET.STYLE_IDS):
                img = self.loader(osp.splitext(imgAug_path)[0] + '_%d.png' % (augid))  # range 0-255
                im = np.array(img).astype(np.float32, copy=False)
                im_shape = im.shape
                im_size_min = np.min(im_shape[0:2])
                # - padding to capture border objects
                img_pad_org = int(self.cfg.RET.IMG.PADDING / self.cfg.RET.IMG.MINSIZE * float(im_size_min))
                im_pad = cv2.copyMakeBorder(im, img_pad_org, img_pad_org, img_pad_org, img_pad_org, cv2.BORDER_REFLECT)
                im_scales = [float(self.cfg.RET.IMG.MINSIZE + 2*self.cfg.RET.IMG.PADDING) / float(im_size_min + 2*img_pad_org) * sc for sc in self.scales]
                images_st.append([cv2.resize(im_pad, (f[1], f[0]), interpolation=cv2.INTER_LINEAR) for f in imsizes])
                for i, im in enumerate(images_st[ii]):
                    img = Image.fromarray(im.astype('uint8'), 'RGB')
                    if self.transform is not None:
                        img = self.transform(img)
                        imsize = [img.shape[1], img.shape[2]]
                    # append images and image sizes
                    images_st[ii][i] = img

        imsize_base = imsizes[0]
        idx_tmp = np.where(self.prop_data_1['info_vec'][:, 1] == img_id)[0]
        queries = {}
        queries['rois'] = self.prop_data_1['info_vec'][idx_tmp, 2:6].tolist().copy()
        queries['labels'] = self.prop_data_1['info_vec'][idx_tmp, 7].tolist().copy()
        queries['rois_rel'] = self.prop_data_1['info_vec'][idx_tmp, 8:12].tolist().copy()
        queries['quids'] = self.prop_data_1['info_vec'][idx_tmp, 0].tolist().copy()

        # - rois loading
        ifv2_img_range = self.prop_data_2['img_range'][img_id].astype(np.int)
        ifv2_rois_rel = self.prop_data_2['info_vec'][ifv2_img_range[0]:ifv2_img_range[1], 8:12]
        ifv2_scales = self.prop_data_2['info_vec'][ifv2_img_range[0]:ifv2_img_range[1], 6]
        ifv2_rois = ifv2_rois_rel * np.array([imsize_base[1],
                                              imsize_base[0],
                                              imsize_base[1],
                                              imsize_base[0]]).reshape(1, 4)
        # - get proposals
        proposals = dict()
        proposals['rois'] = ifv2_rois
        proposals['rois_rel'] = ifv2_rois_rel
        proposals['scales'] = ifv2_scales
        proposals['scales'] = torch.Tensor(proposals['scales'])

        # - imagenames
        imgids = torch.IntTensor([img_id] * len(queries['labels']))
        queries['rois'] = torch.Tensor(queries['rois'])
        queries['rois_rel'] = torch.Tensor(queries['rois_rel'])
        proposals['rois'] = torch.Tensor(proposals['rois'])
        proposals['rois_rel'] = torch.Tensor(proposals['rois_rel'])
        imsizes = [torch.Tensor(imsize) for imsize in imsizes]

        # - find correct scales (smallest scale with min feature dim 5 pixels)
        psize = self.cfg.RET.NETWORK.POOLING.SIZE
        # - queries
        mside = torch.min(torch.stack((queries['rois'][:, 2]-queries['rois'][:, 0], queries['rois'][:, 3] - queries['rois'][:, 1]), dim=0), dim=0)[0]
        mside_f = torch.mul(mside, 1/self.f_stride).unsqueeze(dim=1)
        queries['rois_scale'] = torch.argmin(torch.abs(torch.mul(mside_f, torch.tensor(self.scales).unsqueeze(dim=0)) - (psize + 0.5)), dim=1)
        # - proposals
        mside = torch.min(torch.stack((proposals['rois'][:, 2]-proposals['rois'][:, 0], proposals['rois'][:, 3] - proposals['rois'][:, 1]), dim=0), dim=0)[0]
        mside_f = torch.mul(mside, 1/self.f_stride).unsqueeze(dim=1)
        proposals['rois_scale'] = torch.argmin(torch.abs(torch.mul(mside_f, torch.tensor(self.scales).unsqueeze(dim=0)) - (psize + 0.5)), dim=1)

        return images, images_st, imgids, imsizes, queries, proposals

    def __len__(self):
        return len(self.images_fn)

    def __repr__(self):
        fmt_str = 'Dataset ' + self.__class__.__name__ + '\n'
        fmt_str += '    Number of images: {}\n'.format(self.__len__())
        fmt_str += '    Root Location: {}\n'.format(self.root)
        tmp = '    Transforms (if any): '
        fmt_str += '{0}{1}\n'.format(tmp, self.transform.__repr__().replace('\n', '\n' + ' ' * len(tmp)))
        return fmt_str


