import sys
import torch
import torch.nn as nn
import torch.nn.functional as F
import torchvision
import numpy as np

sys.path.append('external/PreciseRoIPooling/pytorch/prroi_pool')
from prroi_pool import PrRoIPool2D

class _featureExtractor(nn.Module):

    """ Feature extractor """

    def __init__(self, cfg):
        super(_featureExtractor, self).__init__()

        self.cfg = cfg
        pool_size, stride = cfg.RET.NETWORK.POOLING.SIZE, self.feature_map_stride
        if cfg.RET.NETWORK.POOLING.TYPE == 'pool':
            self.roi_pool = lambda input, rois: \
                torchvision.ops.roi_pool(input, rois, (pool_size, pool_size), 1.0 / stride)
        elif cfg.RET.NETWORK.POOLING.TYPE == 'align':
            self.roi_pool = lambda input, rois: \
                torchvision.ops.roi_align(input, rois, (pool_size, pool_size), 1.0 / stride)
        elif cfg.RET.NETWORK.POOLING.TYPE == 'precise':
            self.roi_pool = PrRoIPool2D(pool_size, pool_size, 1.0 / stride)
        else:
            raise ValueError('Uknown pooling % s' % (cfg.RET.NETWORK.POOLING.TYPE))

    def forward(self, im_data, im_data_st, imsize, proposals, scales, get_activation=False):

        boxes = proposals['rois'].data
        boxes_rel = proposals['rois_rel']
        boxes_scale = proposals['rois_scale']

        # - base feature map
        if len(im_data_st) == 0:
            base_feat = [self.FEATNET(im) for im in im_data]

        elif self.cfg.RET.STYLE_AGGTYPE == 'concat':
            base_feat = []
            max_pool = torch.nn.MaxPool2d(kernel_size=5, stride=2, padding=2, dilation=1, ceil_mode=False)
            for sc in range(len(im_data)):
                for ii in range(len(im_data_st)):
                    if ii == 0:
                        base_feat.append(self.FEATNET(im_data[sc]))
                        base_feat[sc] = torch.cat([base_feat[sc], self.FEATNET(im_data_st[ii][sc])], dim=1)
                    else:
                        base_feat[sc] = torch.cat([base_feat[sc], self.FEATNET(im_data_st[ii][sc])], dim=1)
                base_feat[sc] = max_pool(base_feat[sc])

        elif self.cfg.RET.STYLE_AGGTYPE == 'mean':
            base_feat = []
            max_pool = torch.nn.MaxPool2d(kernel_size=5, stride=2, padding=2, dilation=1, ceil_mode=False)
            for sc in range(len(im_data)):
                for ii in range(len(im_data_st)):
                    if ii == 0:
                        base_feat.append(self.FEATNET(im_data[sc]))
                        base_feat[sc] += self.FEATNET(im_data_st[ii][sc])
                    else:
                        base_feat[sc] += self.FEATNET(im_data_st[ii][sc])
                base_feat[sc] /= (len(im_data_st) + 1)
                base_feat[sc] = max_pool(base_feat[sc])

        elif self.cfg.RET.STYLE_AGGTYPE == 'max':
            base_feat = []
            max_pool = torch.nn.MaxPool2d(kernel_size=5, stride=2, padding=2, dilation=1, ceil_mode=False)
            for sc in range(len(im_data)):
                for ii in range(len(im_data_st)):
                    if ii == 0:
                        base_feat.append(self.FEATNET(im_data[sc]))
                        base_feat[sc] = torch.max(base_feat[sc], self.FEATNET(im_data_st[ii][sc]))
                    else:
                        base_feat[sc] = torch.max(base_feat[sc], self.FEATNET(im_data_st[ii][sc]))
                base_feat[sc] = max_pool(base_feat[sc])

        else:
            raise ValueError('Unknown style aggregation: %s' % (self.cfg.RET.STYLE_AGGTYPE))

        # - add batch label to rois
        rois = torch.zeros([boxes.size(0), boxes.size(1), boxes.size(2)+1], dtype=torch.float32)
        if self.cfg.RET.CUDA:
            rois = rois.cuda()
        for ii in range(boxes.size(0)):
            rois[ii, :, 0] = ii * torch.ones(boxes[ii, :, 0].size())  # batch index
            rois[ii, :, 1:5] = boxes[ii, :, 0:4]
        # - add batch label to rois_rel
        rois_rel = torch.zeros([boxes_rel.size(0), boxes_rel.size(1), boxes_rel.size(2)+1], dtype=torch.float32)
        if self.cfg.RET.CUDA:
            rois_rel = rois_rel.cuda()
        for ii in range(boxes_rel.size(0)):
            rois_rel[ii, :, 0] = ii * torch.ones(boxes_rel[ii, :, 0].size())  # batch index
            rois_rel[ii, :, 1:5] = boxes_rel[ii, :, 0:4]
        assert rois.shape[0] == 1, 'no batch implementation available'

        # - extract rois on different scales
        pooled_feat = []
        idx_tmp = []
        for i, sc in enumerate(scales):
            idx_tmp.append(np.where((boxes_scale == i).squeeze())[0])
            rois_tmp = rois[:, (boxes_scale == i).squeeze(), :]
            rois_tmp = rois_tmp * scales[i]  # scale rois
            pooled_feat.append(self.roi_pool(base_feat[i], rois_tmp.view(-1, 5)))
        idx_tmp = np.concatenate(idx_tmp)
        pooled_feat = torch.cat(pooled_feat, dim=0)
        pooled_feat_tmp = pooled_feat
        pooled_feat_tmp[idx_tmp, :, :, :] = pooled_feat

        # - get feature activation
        if get_activation:
            pooled_activation = torch.sum(pooled_feat, axis=[1, 2, 3])
        else:
            pooled_activation = torch.Tensor([])

        # - normalize over each pooled feature
        if self.cfg.RET.PERPOOL_FEATNORM:
            pooled_feat = F.normalize(pooled_feat, p=2, dim=1)
        # - change dimension
        pooled_feat = pooled_feat.view(pooled_feat.shape[0], -1)
        # - normalize over feature
        if self.cfg.RET.FEATNORM:
            pooled_feat = F.normalize(pooled_feat, p=2, dim=1)
        # - feature reduction
        if self.featred_model:
            pooled_feat_tmp = torch.add(pooled_feat, -self.featred_model[0])
            pooled_feat_tmp = pooled_feat_tmp.mm(self.featred_model[1])
            if len(self.featred_model) == 3:    # pca with whitening
                pooled_feat_tmp /= torch.sqrt(self.featred_model[2])
            pooled_feat = pooled_feat_tmp
            # - normalization after feature reduction
            if self.cfg.RET.PCA_FEATNORM:
                pooled_feat = F.normalize(pooled_feat, p=2, dim=1)
        # - change format
        rois = rois.view(-1, 5)
        rois_rel = rois_rel.view(-1, 5)

        return rois, rois_rel, pooled_feat, pooled_activation

    def create_architecture(self):
        self._init_modules()

