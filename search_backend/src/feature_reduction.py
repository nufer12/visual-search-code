import os.path as osp
import numpy as np
import time
import h5py
import pickle
from tqdm import tqdm
import logging

import torch
from torchvision import transforms

from sklearn.decomposition import PCA

from src import get_filenames, proposals
from src.genericdataset import ImagesFromList_v2
from src.utils import check_dir, create_dir, get_mem



def sample_feature_pool(featureExtractor, prop_data, dataset, cfg, num_sample_images, num_sample_patches, filename):

    tf1 = time.time()
    mf1 = get_mem()

    print("test")

    if osp.exists(osp.join(filename)) & cfg.SAVELOAD.FEATPOOL_LOAD:
        logging.info('Load pool of features ... ')
        with h5py.File(osp.join(filename), 'r') as hf:
            feat_pool = np.array(hf.get('data_1'))

        logging.info('Load pool of features took: %3.2f (%3.2f / %3.2f GB)' % (time.time()-tf1, get_mem() - mf1, get_mem()))
        return feat_pool

    # - if feature pool does not exist -> sample feature pool
    logging.info('Extract pool of features ... ')

    # - initialize Dataset
    normalize = transforms.Normalize(
        mean=cfg.NETWORK.PIXELMEAN,
        std=cfg.NETWORK.PIXELSTD
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
        ImagesFromList_v2(prop_data_sample, prop_data_sample['img_ids'], dataset, cfg, scales=cfg.IMG.SCALES, bbxs=[], transform=transform, f_stride=featureExtractor.feature_map_stride),
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
            if cfg.CUDA:
                images = [img.cuda() for img in images]
                for ii in range(len(images_aug)):
                    images_aug[ii] = [img.cuda() for img in images_aug[ii]]
                imsizes = [imsize.cuda() for imsize in imsizes]
                prop['rois'] = prop['rois'].cuda()

            rois_out, rois_out_rel, feat, _ = featureExtractor(images, images_aug, imsizes, prop, cfg.IMG.SCALES)
            # - convert to cpu
            feat_np = feat.cpu().numpy().copy()
            # - sample feature and save to list
            idx_rand = np.random.choice(feat_np.shape[0], min(feat_np.shape[0], num_sample_patches), replace=False)
            featpool_sample.append(list(feat_np[idx_rand, :]))

    # - concatenate
    feat_pool = np.concatenate(featpool_sample, axis=0)

    # - save feature pool
    if cfg.SAVELOAD.FEATPOOL_SAVE:
        #with h5py.File(osp.join(featpool_path, featpool_filename), 'w') as hf:
        with h5py.File(osp.join(filename), 'w') as hf:
            hf.create_dataset('data_1', data=feat_pool)

    # - Time for feature sampling
    logging.info('Extract pool of features took: %3.2f (%3.2f / %3.2f GB)' % (time.time()-tf1, get_mem() - mf1, get_mem()))

    return feat_pool




def compute_pca(featureExtractor, prop_data, dataset, cfg):

    featpool_path = create_dir(osp.join(cfg.OUTPUT_DIR, 'initialization', 'featpool'))
    featpool_filename = get_filenames.featpool1Filename(cfg)

    feat_pool = sample_feature_pool(featureExtractor,
                                    prop_data,
                                    dataset,
                                    cfg,
                                    filename=osp.join(featpool_path, featpool_filename),
                                    num_sample_images=cfg.FEATPOOL1.NUM_IMAGE,
                                    num_sample_patches=cfg.FEATPOOL1.NUM_PATCH)

    # - learn
    tt1 = time.time()
    mm1 = get_mem()

    featred_path = create_dir(osp.join(cfg.OUTPUT_DIR, 'initialization', 'featreduce'))
    featred_filename = get_filenames.featred1Filename(cfg)

    if osp.exists(osp.join(featred_path, featred_filename)) & cfg.SAVELOAD.FEATRED_LOAD:
        # - load feature reduction model
        with open(osp.join(featred_path, featred_filename), 'rb') as file:
            featred_model = pickle.load(file)
    else:
        # - compute feature reduction model
        if cfg.FEAT_REDUCT.TYPE != 'none':
            if cfg.FEAT_REDUCT.TYPE =='pcaw':
                logging.info('Computing pca ... ')
                featred_model = PCA(n_components=cfg.FEAT_REDUCT.DIMENSION, whiten=True)
                t_pca_start = time.time()
                m_pca_start = get_mem()
                featred_model.fit(feat_pool)
                logging.info('Computing pca took %3.2f seconds' % (time.time() - t_pca_start))
                # Information
                # -----------------------
                # x = feat_pool[0:5, :]
                # f_gt = featred_model.transform(x)
                # f_pred = (x - featred_model.mean_).dot(featred_model.components_.T)
                # f_pred /= np.sqrt(featred_model.explained_variance_)
                # print(np.max(f_gt - f_pred))

            elif cfg.FEAT_REDUCT.TYPE =='pca':
                logging.info('Computing pca ... ')
                featred_model = PCA(n_components=cfg.FEAT_REDUCT.DIMENSION, whiten=False)
                t_pca_start = time.time()
                m_pca_start = get_mem()
                featred_model.fit(feat_pool)
                logging.info('Computing pca took %3.2f seconds' % (time.time() - t_pca_start))
                # Information
                # -----------------------
                # x = feat_pool[0:5, :]
                # f_gt = featred_model.transform(x)
                # f_pred = (x - featred_model.mean_).dot(featred_model.components_.T)
                # f_pred /= np.sqrt(featred_model.explained_variance_)
                # print(np.max(f_gt - f_pred))

            else:
                raise ValueError("Uknown feature reduction: %s" % cfg.FEAT_REDUCT.TYPE)

            # - save feature reduction model
            if cfg.SAVELOAD.FEATRED_SAVE:
                t_featred_save = time.time()
                logging.info('Saving feature reduction model ...')
                with open(osp.join(featred_path, featred_filename), 'wb') as file:
                    pickle.dump(featred_model, file, protocol=4)
                logging.info('Saving feature reduction model took %3.2f seconds' % (time.time() - t_featred_save))

    logging.info('Overall feature reduction computation took : %3.2f (%3.2f / %3.2f GB)' % (time.time()-tt1, get_mem() - mm1, get_mem()))

    return featred_model





