from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
import logging

import torch
import torch.nn as nn
from torchvision.models import alexnet

from networks.feature_extractor import _featureExtractor


# - Alexnet
class ALEXNET(_featureExtractor):

    def __init__(self, cfg, featred_model=[], pretrained=True):
        self.model_path = cfg.RET.NETWORK.WEIGHTS
        self.pretrained = pretrained
        self.layer = cfg.RET.NETWORK.LAYER
        self.mean = cfg.RET.NETWORK.PIXELMEAN
        self.std = cfg.RET.NETWORK.PIXELSTD
        self.featred_model = []
        if featred_model:
            self.featred_model.append(featred_model.mean_)
            self.featred_model.append(featred_model.components_.T)
        self.cfg = cfg

        if self.layer not in ['block1', 'block2', 'block3', 'block4', 'block5']:
            raise ValueError('The configuration %s is not available' % (self.layer))

        if self.layer == 'block1':
            self.layer_cut = 2
            self.feature_map_dim = 64
            self.feature_map_stride = 4 * 2
        elif self.layer == 'block2':
            self.layer_cut = 5
            self.feature_map_dim = 192
            self.feature_map_stride = 8 * 2
        elif self.layer == 'block3':
            self.layer_cut = 8
            self.feature_map_dim = 384
            self.feature_map_stride = 16 * 2
        elif self.layer == 'block4':
            self.layer_cut = 10
            self.feature_map_dim = 256
            self.feature_map_stride = 16 * 2
        elif self.layer == 'block5':
            self.layer_cut = 12
            self.feature_map_dim = 256
            self.feature_map_stride = 16 * 2

        _featureExtractor.__init__(self, cfg)

    def _set_featred_model(self, featred_model):
        self.featred_model.append(torch.Tensor(featred_model.mean_))
        self.featred_model.append(torch.Tensor(featred_model.components_.T))
        if featred_model.whiten:
            self.featred_model.append(torch.Tensor(featred_model.explained_variance_))
        self.featred_model_debug = featred_model
        if self.cfg.RET.CUDA:
            for i in range(len(self.featred_model)):
                self.featred_model[i] = self.featred_model[i].cuda()

    def _init_modules(self):
        modules = alexnet().features[0:self.layer_cut]
        self.FEATNET = nn.Sequential(*modules)
        if self.pretrained:
            model_dict = self.FEATNET.state_dict()
            pretrained_dict = alexnet(pretrained=True).features.state_dict()
            pretrained_dict = {k: v for k, v in list(pretrained_dict.items()) if k in model_dict}
            model_dict.update(pretrained_dict)
            self.FEATNET.load_state_dict(model_dict)
            logging.info([k for k, v in list(pretrained_dict.items())])

        # fix all layers
        for param in self.FEATNET.parameters():
            param.requires_grad = False

        # - set evaluation mode
        self.FEATNET.eval()

