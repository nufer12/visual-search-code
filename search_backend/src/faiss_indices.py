import os
import os.path as osp
import numpy as np
import time
import logging
import faiss
import h5py

import torch
from torchvision import transforms

from src import faiss_indices, get_filenames
from src.genericdataset import ImagesStylizationsFromList
from src.utils import create_dir
from src.feature_reduction import sample_feature_pool

# PQ Quantization: The number of bits n_bits must be equal to 8, 12 or 16. The dimension d should be a multiple of m.

def make_gpu_multiple_cloner_options(use_float16=True,
                                     use_float16_coarse_quantizer=False,
                                     use_precomputed_tables=True,
                                     indices_options=faiss.INDICES_CPU,
                                     reserve_vecs=None,
                                     shard=True):
    cloner_options = faiss.GpuMultipleClonerOptions()
    cloner_options.useFloat16 = use_float16
    cloner_options.useFloat16CoarseQuantizer = use_float16_coarse_quantizer
    cloner_options.usePrecomputed = use_precomputed_tables
    cloner_options.indicesOptions = indices_options
    cloner_options.shard = shard
    if reserve_vecs:
        cloner_options.reserveVecs = reserve_vecs
    return cloner_options


def train(featureExtractor, prop_data, dataset, cfg):
    """ Train search index based on sampled features """

    # - get feature dimension
    if cfg.RET.FEAT_REDUCT.TYPE == 'none':
        fdim = featureExtractor.dout_base_model * (cfg.RET.NETWORK.POOLING.SIZE ** 2)
    else:
        fdim = cfg.RET.FEAT_REDUCT.DIMENSION

    # - initialize feature index
    if 'IVFPQ' in cfg.RET.FAISS.TYPE:
        # - get parameters
        index_parameter = cfg.RET.FAISS.TYPE.split('_')
        numQuantizers, nbits, numCentroids, nprobe = [int(index_parameter[i]) for i in range(1, len(index_parameter))]
        coarseQuantizer = faiss.IndexFlatL2(fdim)
        index = faiss.IndexIVFPQ(coarseQuantizer, fdim, numCentroids, numQuantizers, nbits)
        index.nprobe = nprobe
    else:
        raise ValueError('Unknown index type: %s' % (type))

    # - sample feature pool for training
    featpool_path = create_dir(osp.join(cfg.OUTPUT_DIR, 'initialization', 'featpool'))
    featpool_filename = get_filenames.featredpool2Filename(cfg)
    feat_pool = sample_feature_pool(featureExtractor,
                                    prop_data,
                                    dataset,
                                    cfg,
                                    filename=osp.join(featpool_path, featpool_filename),
                                    num_sample_images=cfg.RET.FEATPOOL2.NUM_IMAGE,
                                    num_sample_patches=cfg.RET.FEATPOOL2.NUM_PATCH)
    torch.cuda.empty_cache()

    # - train search index based on feature pool
    index.train(feat_pool)

    # - index version on cpu
    index_cpu = index
    if cfg.RET.FAISS.GPU:
        logging.info('Available gpu: %d' % (faiss.get_num_gpus()))
        co = make_gpu_multiple_cloner_options()
        # - move index to gpu
        index = faiss.index_cpu_to_all_gpus(index, co=co)

    return index, index_cpu


def pqRecon_train(featureExtractor, prop_data, dataset, gpus, cfg):

    """ Train pq quantizer for storing feature on  disk """

    # - get feature dimension
    if cfg.RET.FEAT_REDUCT.TYPE == 'none':
        fdim = featureExtractor.dout_base_model * (cfg.RET.NETWORK.POOLING.SIZE ** 2)
    else:
        fdim = cfg.RET.FEAT_REDUCT.DIMENSION

    tf1 = time.time()
    logging.info("Training PQ quantization: ")

    pqRecon_parameter = cfg.RET.FAISS.PQRECONTYPE.split('_')
    numQuantizers, nbits = [int(pqRecon_parameter[i]) for i in range(1, len(pqRecon_parameter))]

    pqRecon = faiss.IndexPQ(fdim, numQuantizers, nbits)

    featpool_path = create_dir(osp.join(cfg.OUTPUT_DIR, 'initialization', 'featpool'))
    featpool_filename = get_filenames.featredpool2Filename(cfg)
    from src.feature_reduction import sample_feature_pool
    feat_pool = sample_feature_pool(featureExtractor,
                                    prop_data,
                                    dataset,
                                    cfg,
                                    filename=osp.join(featpool_path, featpool_filename),
                                    num_sample_images=cfg.RET.FEATPOOL2.NUM_IMAGE,
                                    num_sample_patches=cfg.RET.FEATPOOL2.NUM_PATCH)

    pqRecon.train(feat_pool)

    logging.info("Training pqRecon took %3.2f sec" % (time.time()-tf1))

    return pqRecon


def populate(index, pqRecon, featureExtractor, prop_data, dataset, gpus, cfg):
    """ Populate trained index with local features of all images """

    logging.info('Populate index')
    tfa_1 = time.time()

    # Initialize Dataset
    normalize = transforms.Normalize(
        mean=cfg.RET.NETWORK.PIXELMEAN,
        std=cfg.RET.NETWORK.PIXELSTD
    )
    transform = transforms.Compose([
        transforms.ToTensor(),
        normalize
    ])
    loader = torch.utils.data.DataLoader(
        ImagesStylizationsFromList(prop_data, dataset['images_ret'], dataset, cfg, scales=cfg.RET.IMG.SCALES,
                                    transform=transform, f_stride=featureExtractor.feature_map_stride),
        batch_size=1,
        shuffle=False,
        num_workers=1,
        pin_memory=True)

    # - create pqRecon_hdf5 file for saving pq codes
    pqReconh5_file = osp.join(osp.join(cfg.OUTPUT_DIR, 'initialization', 'pqRecon'), get_filenames.pqReconh5Filename_exp(cfg))
    if osp.exists(pqReconh5_file):
        os.remove(pqReconh5_file)
    pqRecon_hdf5 = h5py.File(pqReconh5_file, 'a')
    pqRecon_dim = int(cfg.RET.FAISS.PQRECONTYPE.split('_')[1])
    pqRecon_hdf5.create_dataset('features', (0, pqRecon_dim), maxshape=(None, pqRecon_dim), dtype=np.uint8, chunks=True)

    # - initialize info_vec for local patch information
    info_vec = np.zeros([len(loader) * 5000, 6 + 1 + 1], dtype=np.int32)  # zeros -> labels default
    info_vec_imgrange = np.zeros([len(dataset['imagelist']), 2], dtype=np.int32)

    info_vec_count = 0
    for i, (images, images_aug, imgids, imsizes, proposals, _) in enumerate(loader):

        if len(proposals) == 0:
            logging.info('No rois --> continue ...')
            continue

        if proposals['rois'].size()[1] == 0:
            logging.info('No rois --> continue ...')
            continue

        if cfg.RET.CUDA:
            images = [img.cuda() for img in images]
            for ii in range(len(images_aug)):
                images_aug[ii] = [img.cuda() for img in images_aug[ii]]
            imsizes = [imsize.cuda() for imsize in imsizes]
            proposals['rois'] = proposals['rois'].cuda()

        # - feature extraction
        num_rois = proposals['rois'].shape[1]
        if cfg.RET.DISCPROP.MAX < num_rois:
            rois_out, rois_out_rel, feat, act = featureExtractor(images, images_aug, imsizes, proposals, cfg.RET.IMG.SCALES, get_activation=True)
            idx_sort = torch.argsort(act, descending=True)
            idx_sort = idx_sort[0:cfg.RET.DISCPROP.MAX]
            feat = feat[idx_sort, :]
            rois_out = rois_out[idx_sort, :]
            rois_out_rel = rois_out_rel[idx_sort, :]
        else:
            rois_out, rois_out_rel, feat, _ = featureExtractor(images, images_aug, imsizes, proposals, cfg.RET.IMG.SCALES)

        # - convert to cpu
        rois_rel_np = rois_out_rel.cpu().numpy().copy()
        rois_np = rois_out.cpu().numpy().copy()
        feat_np = feat.cpu().numpy().copy()

        # - remove and clear cache
        if (i+1) % 50 == 0:
            del rois_out, rois_out_rel, feat
            torch.cuda.empty_cache()
            if gpus:
                logging.info('GPU Memory: ' + gpus.reportstr())

        for ii in np.arange(0, feat_np.shape[0], 1000):
            index.add(feat_np[ii:ii + 1000, :].astype('float32').copy())

        # - save pq codes to file (for query expansion)
        hdf5_length = pqRecon_hdf5['features'].shape[0]
        pqRecon_hdf5["features"].resize((hdf5_length + feat_np.shape[0]), axis=0)
        pqRecon_hdf5["features"][hdf5_length:] = pqRecon.pq.compute_codes(feat_np)

        # - add to info vector
        for ii in range(1):
            idx_tmp = np.where(rois_np[:, 0] == ii)[0]
            # - scale rois back to original size
            rois_rel_tmp = rois_rel_np[idx_tmp, 1:5]
            imgids_tmp = [imgids[0][ii] for ii in idx_tmp]
            scales = [int(proposals['scales'][0][ii].numpy()) for ii in idx_tmp]
            # - create info_vec for all patches images
            info_vec_imgrange[int(imgids_tmp[0].numpy()), :] = [info_vec_count, info_vec_count+rois_rel_tmp.shape[0]-1]
            # - create info_vec for all patches images
            for jj in range(rois_rel_tmp.shape[0]):
                # - [img_id, x1, y1, x2, y2, scale]
                info_vec[info_vec_count, 0] = info_vec_count
                info_vec[info_vec_count, 1] = imgids_tmp[jj].numpy()
                info_vec[info_vec_count, 2:6] = (rois_rel_tmp[jj, :].reshape(1, -1) * cfg.RET.INFOVEC.BBSSCALE).astype(np.uint32)
                info_vec[info_vec_count, 6] = scales[jj]
                info_vec_count += 1
        if ((i+1) % 10) == 0:
            logging.info('Add feature to index: %d/%d %3.2f sec' % (i+1, len(loader), time.time() - tfa_1))

    info_vec = info_vec[0:info_vec_count, :]
    logging.info('Adding feature to index took %d: %3.2f sec', i, time.time() - tfa_1)
    pqRecon_hdf5.close()

    return index, info_vec, info_vec_imgrange


def generate_index(featureExtractor, prop_data, dataset, gpus, cfg):

    """ Generate index incl training """

    index_path = create_dir(osp.join(cfg.OUTPUT_DIR, 'initialization', 'index'))
    index_filename = get_filenames.indexFilename(cfg)
    pqRecon_path = create_dir(osp.join(cfg.OUTPUT_DIR, 'initialization', 'pqRecon'))
    pqRecon_filename = get_filenames.pqReconFilename(cfg)
    infovec_filename = get_filenames.infovecFilename(cfg)
    infovecimgrange_filename = get_filenames.infovecimgrangeFilename(cfg)

    if osp.exists(osp.join(cfg.OUTPUT_DIR, 'initialization', 'pqRecon', get_filenames.pqReconh5Filename_exp(cfg))) & \
       osp.exists(osp.join(index_path, index_filename)) & cfg.RET.SAVELOAD.INDEX_LOAD:
        logging.info('Loading faiss index ...')
        tt1 = time.time()
        index = faiss.read_index(osp.join(index_path, index_filename))
        pqRecon = faiss.read_index(osp.join(pqRecon_path, pqRecon_filename))
        with h5py.File(osp.join(index_path, infovec_filename), 'r') as hf:
            info_vec = np.array(hf['info_vec'])
        with h5py.File(osp.join(index_path, infovecimgrange_filename), 'r') as hf:
            info_vec_imgrange = np.array(hf['info_vec_imgrange'])
        logging.info('Loading faiss index overall took %3.2f seconds' % (time.time() - tt1))

        if cfg.RET.FAISS.GPU:
            logging.info('Available gpu: %d' % (faiss.get_num_gpus()))
            co = make_gpu_multiple_cloner_options()
            index = faiss.index_cpu_to_all_gpus(index, co=co)

    else:
        tt1 = time.time()
        index, index_cpu = faiss_indices.train(featureExtractor, prop_data, dataset, cfg)
        logging.info('Train faiss index: %3.2f seconds' % (time.time()-tt1))
        torch.cuda.empty_cache()
        if gpus:
            logging.info('GPU Memory: ' + gpus.reportstr())
        if cfg.RET.PQRECON_INDEX:
            pqRecon = index_cpu
        else:
            tt1 = time.time()
            pqRecon = faiss_indices.pqRecon_train(featureExtractor, prop_data, dataset, gpus, cfg)
            logging.info('Train faiss pqRecon: %3.2f seconds' % (time.time()-tt1))
            torch.cuda.empty_cache()
            if gpus:
                logging.info('GPU Memory: ' + gpus.reportstr())

        index, info_vec, info_vec_imgrange, = faiss_indices.populate(index,
                                                                     pqRecon,
                                                                     featureExtractor,
                                                                     prop_data,
                                                                     dataset,
                                                                     gpus,
                                                                     cfg)
        torch.cuda.empty_cache()
        if gpus:
            logging.info('GPU Memory: ' + gpus.reportstr())
        if cfg.RET.SAVELOAD.INDEX_SAVE:
            t1_saveindex = time.time()
            if cfg.RET.FAISS.GPU:
                faiss.write_index(faiss.index_gpu_to_cpu(index), osp.join(create_dir(index_path), index_filename))
            else:
                faiss.write_index(index, osp.join(create_dir(index_path), index_filename))
            faiss.write_index(pqRecon, osp.join(create_dir(pqRecon_path), pqRecon_filename))
            with h5py.File(osp.join(index_path, infovec_filename), 'w') as hf:
                hf.create_dataset('info_vec', data=info_vec)
            with h5py.File(osp.join(index_path, infovecimgrange_filename), 'w') as hf:
                hf.create_dataset('info_vec_imgrange', data=info_vec_imgrange)
            logging.info('Write index and save info_vec took %3.2f seconds' % (time.time() - t1_saveindex))

    return index, info_vec, info_vec_imgrange, pqRecon




