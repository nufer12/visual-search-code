import os.path as osp
import numpy as np
import time
import h5py
import pickle
from tqdm import tqdm
import logging
from sklearn.decomposition import PCA
import torch
from torchvision import transforms

from src import get_filenames, proposals, utils
from src.genericdataset import ImagesStylizationsFromList


def sample_feature_pool(featureExtractor, prop_data, dataset, cfg, num_sample_images, num_sample_patches, filename, always_load=False):
    """ Sample feature pool """

    tf1 = time.time()
    # - if feature pool exists -> load
    if osp.exists(osp.join(filename)) & (cfg.RET.SAVELOAD.FEATPOOL_LOAD or always_load):
        logging.info('Load pool of features ... ')
        # - load feature pool if available
        with h5py.File(osp.join(filename), 'r') as hf:
            feat_pool = np.array(hf.get('data_1'))
        logging.info('Load pool of features took: %3.2f' % (time.time()-tf1))
        return feat_pool
    # - if feature pool does not exist -> sample feature pool
    logging.info('Extract pool of features ... ')
    # - initialize dataset
    normalize = transforms.Normalize(
        mean=cfg.RET.NETWORK.PIXELMEAN,
        std=cfg.RET.NETWORK.PIXELSTD
    )
    transform = transforms.Compose([
        transforms.ToTensor(),
        normalize
    ])
    # - sample images for feature pooling
    num_images = min(num_sample_images, len(dataset['images_ret']))
    num_patches = num_sample_patches
    prop_data_sample = proposals.sample_prop_data(prop_data.copy(), dataset, num_images, num_patches, cfg.RANDSEED)
    loader_featpool = torch.utils.data.DataLoader(
        ImagesStylizationsFromList(prop_data_sample, prop_data_sample['img_ids'], dataset, cfg,
                                   scales=cfg.RET.IMG.SCALES, bbxs=[], transform=transform,
                                   f_stride=featureExtractor.feature_map_stride),
                                   batch_size=1,
                                   shuffle=False,
                                   num_workers=1,
                                   pin_memory=True)

    featpool_sample = []
    for i, (images, images_aug, imgids, imsizes, prop, _) in tqdm(enumerate(loader_featpool)):
        if len(prop) == 0:
            logging.info('No rois --> continue ...')
            continue
        if prop['rois'].size()[1] == 0:
            logging.info('No rois --> continue ...')
            continue
        with torch.no_grad():
            if cfg.RET.CUDA:
                images = [img.cuda() for img in images]
                for ii in range(len(images_aug)):
                    images_aug[ii] = [img.cuda() for img in images_aug[ii]]
                imsizes = [imsize.cuda() for imsize in imsizes]
                prop['rois'] = prop['rois'].cuda()
            # - extract features
            rois_out, rois_out_rel, feat, _ = featureExtractor(images, images_aug, imsizes, prop, cfg.RET.IMG.SCALES)
            # - sample feature and save to list
            feat_np = feat.cpu().numpy().copy()
            idx_rand = np.random.choice(feat_np.shape[0], min(feat_np.shape[0], num_sample_patches), replace=False)
            featpool_sample.append(list(feat_np[idx_rand, :]))
    # - concatenate
    feat_pool = np.concatenate(featpool_sample, axis=0)
    # - save feature pool
    if cfg.RET.SAVELOAD.FEATPOOL_SAVE:
        with h5py.File(osp.join(filename), 'w') as hf:
            hf.create_dataset('data_1', data=feat_pool)
    # - time for feature sampling
    logging.info('Extract pool of features took: %3.2f' % (time.time()-tf1))
    return feat_pool


def compute_pca(featureExtractor, prop_data, dataset, cfg):
    """ Computer pca reduction model """

    tt1 = time.time()
    featred_path = utils.create_dir(osp.join(cfg.OUTPUT_DIR, 'initialization', 'featreduce'))
    featred_filename = get_filenames.featred1Filename(cfg)
    if osp.exists(osp.join(featred_path, featred_filename)) & cfg.RET.SAVELOAD.FEATRED_LOAD:
        # - load feature reduction model
        with open(osp.join(featred_path, featred_filename), 'rb') as file:
            featred_model = pickle.load(file)
    else:
        # - sample pool of features
        featpool_path = utils.create_dir(osp.join(cfg.OUTPUT_DIR, 'initialization', 'featpool'))
        featpool_filename = get_filenames.featpool1Filename(cfg)
        feat_pool = sample_feature_pool(featureExtractor,
                                        prop_data,
                                        dataset,
                                        cfg,
                                        filename=osp.join(featpool_path, featpool_filename),
                                        num_sample_images=cfg.RET.FEATPOOL1.NUM_IMAGE,
                                        num_sample_patches=cfg.RET.FEATPOOL1.NUM_PATCH)
        # - compute feature reduction model
        if cfg.RET.FEAT_REDUCT.TYPE != 'none':
            if cfg.RET.FEAT_REDUCT.TYPE =='pcaw':
                logging.info('Computing pca ... ')
                featred_model = PCA(n_components=cfg.RET.FEAT_REDUCT.DIMENSION, whiten=True)
                t_pca_start = time.time()
                featred_model.fit(feat_pool)
                logging.info('Computing pca took %3.2f seconds' % (time.time() - t_pca_start))
            elif cfg.RET.FEAT_REDUCT.TYPE =='pca':
                logging.info('Computing pca ... ')
                featred_model = PCA(n_components=cfg.RET.FEAT_REDUCT.DIMENSION, whiten=False)
                t_pca_start = time.time()
                featred_model.fit(feat_pool)
                logging.info('Computing pca took %3.2f seconds' % (time.time() - t_pca_start))
            else:
                raise ValueError("Uknown feature reduction: %s" % cfg.RET.FEAT_REDUCT.TYPE)

            # - save feature reduction model
            if cfg.RET.SAVELOAD.FEATRED_SAVE:
                t_featred_save = time.time()
                logging.info('Saving feature reduction model ...')
                with open(osp.join(featred_path, featred_filename), 'wb') as file:
                    pickle.dump(featred_model, file)
                logging.info('Saving feature reduction model took %3.2f seconds' % (time.time() - t_featred_save))
        else:
            featred_model = []

    logging.info('Overall feature reduction computation took : %3.2f' % (time.time()-tt1))
    return featred_model


def load_featredpool2(cfg):
    """ Load feature pool 2 """

    feat_pool_path = utils.create_dir(osp.join(cfg.OUTPUT_DIR, 'initialization', 'featpool'))
    feat_pool_filename = get_filenames.featredpool2Filename(cfg)
    feat_pool = sample_feature_pool([], [], [], cfg,
                                    filename=osp.join(feat_pool_path, feat_pool_filename),
                                    num_sample_images=cfg.RET.FEATPOOL2.NUM_IMAGE,
                                    num_sample_patches=cfg.RET.FEATPOOL2.NUM_PATCH,
                                    always_load=True)
    return feat_pool




