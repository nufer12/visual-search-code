import sys, os
import os.path as osp
import numpy as np
import time
import shutil
import h5py
import faiss
from PIL import Image
import torch
import torch.nn as nn
from torchvision import models, transforms
import torch.utils.data as data
from sklearn.metrics.pairwise import euclidean_distances as skdist
import logging

sys.path.append('./external/PreciseRoIPooling/pytorch/prroi_pool')
from prroi_pool import PrRoIPool2D

from src.utils import create_dir, pil_loader


class Model(nn.Module):
    """ Feature extraction network """

    def __init__(self, cfg):
        super(Model, self).__init__()
        self.cfg = cfg
        self.pooling_size = [5, 5]
        self.featuremap_stride = 16
        self.featuremap_dim = 512
        if cfg.TEMP.NETWORK.WEIGHTS:
            model = models.vgg16_bn()
            model_dict = model.state_dict()
            pretrained_dict = torch.load(cfg.TEMP.NETWORK.WEIGHTS)
            pretrained_dict = {k: v for k, v in list(pretrained_dict.items()) if 'features' in k}
            model_dict.update(pretrained_dict)
            model.load_state_dict(model_dict)
            self.feat = model.features[0:34]
        else:
            self.feat = models.vgg16_bn(pretrained=True).features[0:34]
        self.roi_pool = PrRoIPool2D(self.pooling_size[0], self.pooling_size[1], 1.0/self.featuremap_stride)
        self.feat_pool_dim = np.prod(self.pooling_size) * self.featuremap_dim

    def forward(self, img, img_size):
        # - extract feature map
        feat_map = self.feat(img)
        # - pooling for identical sizes
        rois_tmp = torch.zeros(img.shape[0], 5)
        rois_tmp[:, 0] = torch.arange(0, img.shape[0])
        rois_tmp[:, 1] = torch.zeros(1, img.shape[0])
        rois_tmp[:, 2] = torch.zeros(1, img.shape[0])
        rois_tmp[:, 3] = img_size[:, 0]
        rois_tmp[:, 4] = img_size[:, 1]
        if img_size.is_cuda:
            rois_tmp = rois_tmp.cuda()
        feat_pool = self.roi_pool(feat_map, rois_tmp.view(img.shape[0], -1)).view(img.shape[0], -1)
        return feat_pool


class ImagesList(data.Dataset):
    """ Data loader that loads images dataset """

    def __init__(self, dataset, cfg, transform=None, loader=pil_loader):
        self.dataset = dataset
        self.images = [dataset['imagelist'][i] for i in dataset['images_ret']]
        self.images_id = list(np.arange(0, len(self.images)))
        self.images_fn = [os.path.join(self.dataset['img_path'], f) for f in self.images]
        if len(self.images_fn) == 0:
            raise(RuntimeError("Dataset contains 0 images!"))
        self.transform = transform
        self.loader = loader
        self.cfg = cfg

    def __getitem__(self, index):
        path = self.images_fn[index]
        img_id = self.images_id[index]
        img = self.loader(path)
        if self.transform is not None:
            img = self.transform(img)
            img_size = [img.shape[1], img.shape[2]]
        img_size = torch.IntTensor(img_size)
        return img_id, img, img_size

    def __len__(self):
        return len(self.images_fn)


def featuresFilename(cfg):
    filename = 'net_vgg16bn_pool_%s_%d.h5' % (cfg.TEMP.NETWORK.POOLING.TYPE,
                                              cfg.TEMP.NETWORK.POOLING.SIZE)
    return filename


def compute_style_templates(dataset, cfg):
    """ Finding style templates """

    # Check if templates already exist
    centroidPath = create_dir(osp.join(cfg.OUTPUT_DIR, 'style_cluster/centroids', 'ncluster_%d' % cfg.TEMP.NCLUSTER))
    if osp.exists(centroidPath) & (len(os.listdir(centroidPath)) == cfg.TEMP.NCLUSTER):
        logging.info('Centroids already exist -> continue ...')
        return

    # Network initialization
    model = Model(cfg)
    model.eval()
    if cfg.TEMP.CUDA:
        model = model.cuda()

    # Image Loader
    normalize = transforms.Normalize(
        mean=cfg.TEMP.NETWORK.PIXELMEAN,
        std=cfg.TEMP.NETWORK.PIXELSTD
    )
    transform = transforms.Compose([
        transforms.Resize([cfg.TEMP.IMG_SIZE, cfg.TEMP.IMG_SIZE], interpolation=2),
        transforms.ToTensor(),  # -> map to range [0,1]
        normalize
    ])
    image_loader = torch.utils.data.DataLoader(
        ImagesList(dataset, cfg, transform=transform, loader=pil_loader),
        batch_size=cfg.TEMP.BATCHSIZE, shuffle=False, num_workers=8, pin_memory=True
    )

    features_file = osp.join(create_dir(osp.join(cfg.OUTPUT_DIR, 'style_cluster', 'features')), featuresFilename(cfg))

    if osp.exists(features_file):
        # - load features
        logging.info("Feature file exists -> loading ...")
        t1 = time.time()
        hf = h5py.File(features_file, 'r')
        features = np.array(hf['features'])
        hf.close()
        logging.info("Feature file exists -> loading took %3.2f seconds" % (time.time() - t1))
    else:
        features = np.zeros([len(dataset['imagelist']), model.feat_pool_dim], dtype=np.float32)
        for i, (img_id, img, img_size) in enumerate(image_loader):
            with torch.no_grad():
                logging.info('Iteration:' + str(i) + ' ' + str(len(image_loader)))
                if cfg.TEMP.CUDA:
                    img = img.cuda()
                    img_size = img_size.cuda()
                # - extract and save features
                features[img_id] = model(img, img_size).detach().cpu().numpy()
                if (i+1) % 50:
                    torch.cuda.empty_cache()
        # - save features
        hf = h5py.File(features_file, 'w')
        hf.create_dataset('features', data=features)
        hf.close()

    assert cfg.TEMP.NCLUSTER <= len(dataset['imagelist']), '#clusters > #images in dataset'

    kmeans = faiss.Kmeans(features.shape[1], cfg.TEMP.NCLUSTER, verbose=True)
    kmeans.train(features)
    centroids = kmeans.centroids
    # - find nearest image wrt center
    centroids = np.argmin(skdist(features, centroids), axis=0)

    # - save centroids
    for m in centroids:
        shutil.copy(osp.join(dataset['img_path'], dataset['imagelist'][m]), centroidPath)


