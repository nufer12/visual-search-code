import os
import os.path as osp
import torch
import sys
import numpy as np
import re
import time
from PIL import Image
import logging
import torchvision.utils as vutils
import torch.backends.cudnn as cudnn

from src.utils import check_dir, create_dir

if osp.basename(os.getcwd()) == 'worker':
    sys.path.append('./../external/LinearStyleTransfer')
else:
    sys.path.append('./external/LinearStyleTransfer')
from libs.Loader import Dataset, DatasetImagelist
from libs.Matrix import MulLayer
from libs.utils import print_options
from libs.models import encoder3, encoder4, encoder5
from libs.models import decoder3, decoder4, decoder5


def generate_style_transformations(dataset, cfg):
    """ Perform style transformations based on style templates"""

    centroids_path = check_dir(osp.join(cfg.OUTPUT_DIR, 'style_cluster/centroids/ncluster_%d' % (cfg.TEMP.NCLUSTER)))
    stylized_image_path = create_dir(cfg.TRANS.STYLE_PATH)
    imagelist = [dataset['imagelist'][i] for i in np.unique(dataset['images_ret'] + dataset['images_qu'])]

    if len(os.listdir(stylized_image_path)) >= (cfg.TEMP.NCLUSTER * len(imagelist)):
        logging.info('All style transformations are available --> continue ...')
        return

    if cfg.TRANS.LAYER == 'r31':
        cfg.TRANS.VGG_DIR = osp.join(cfg.TRANS.VGG_DIR, 'vgg_r31.pth')
        cfg.TRANS.DECODER_DIR = osp.join(cfg.TRANS.DECODER_DIR, 'dec_r31.pth')
        cfg.TRANS.MATRIX_PATH = osp.join(cfg.TRANS.MATRIX_PATH, 'r31.pth')
    elif cfg.TRANS.LAYER == 'r41':
        cfg.TRANS.VGG_DIR = osp.join(cfg.TRANS.VGG_DIR, 'vgg_r41.pth')
        cfg.TRANS.DECODER_DIR = osp.join(cfg.TRANS.DECODER_DIR, 'dec_r41.pth')
        cfg.TRANS.MATRIX_PATH = osp.join(cfg.TRANS.MATRIX_PATH, 'r41.pth')
    else:
        raise ValueError('Layer %s ls unknown!' % (cfg.TRANS.LAYER))
        pass

    cudnn.benchmark = True

    ################# MODEL #################
    if(cfg.TRANS.LAYER == 'r31'):
        vgg = encoder3()
        dec = decoder3()
    elif(cfg.TRANS.LAYER == 'r41'):
        vgg = encoder4()
        dec = decoder4()
    matrix = MulLayer(cfg.TRANS.LAYER)
    vgg.load_state_dict(torch.load(cfg.TRANS.VGG_DIR))
    dec.load_state_dict(torch.load(cfg.TRANS.DECODER_DIR))
    matrix.load_state_dict(torch.load(cfg.TRANS.MATRIX_PATH))

    if cfg.TRANS.CUDA:
        vgg.cuda()
        dec.cuda()
        matrix.cuda()

    with torch.no_grad():

        num_styleTemplates = int(re.findall(r'\s*_([0-9]+)', osp.basename(centroids_path))[0])
        logging.info('Number of style templates: %d' % num_styleTemplates)

        ################# DATA #################
        content_dataset = DatasetImagelist(dataset['img_path'],
                                           imagelist,
                                           cfg.TRANS.LOADSIZE,
                                           cfg.TRANS.FINESIZE,
                                           test=True)

        content_loader = torch.utils.data.DataLoader(dataset=content_dataset,
                                                     batch_size=cfg.TRANS.BATCHSIZE,
                                                     shuffle=False,
                                                     num_workers=1)

        style_dataset = Dataset(centroids_path,
                                cfg.TRANS.LOADSIZE,
                                cfg.TRANS.FINESIZE,
                                test=True)

        style_loader = torch.utils.data.DataLoader(dataset=style_dataset,
                                                   batch_size=cfg.TRANS.BATCHSIZE,
                                                   shuffle=False,
                                                   num_workers=1)

        ################# GLOBAL VARIABLE #################
        contentV = torch.Tensor(cfg.TRANS.BATCHSIZE, 3, cfg.TRANS.FINESIZE, cfg.TRANS.FINESIZE)
        styleV = torch.Tensor(cfg.TRANS.BATCHSIZE, 3, cfg.TRANS.FINESIZE, cfg.TRANS.FINESIZE)

        ################# GPU  #################
        if cfg.TRANS.CUDA:
            contentV = contentV.cuda()
            styleV = styleV.cuda()


        for ci, (content, contentName) in enumerate(content_loader):
            logging.info('Number of style templates %s: %d / %d ' % (num_styleTemplates, ci, len(content_loader)))
            contentName = contentName[0]
            if cfg.TRANS.VERBOSE:
                logging.info(content.size())
            contentV.resize_(content.size()).copy_(content)


            for sj, (style, styleName) in enumerate(style_loader):
                styleName = styleName[0]
                styleV.resize_(style.size()).copy_(style)

                stylized_image_file = osp.join(stylized_image_path, '%s_%d.png' % (contentName, sj + 1))

                logging.info(stylized_image_file)

                if osp.exists(stylized_image_file):
                    continue

                for ii in range(100):
                    t1 = time.time()

                    # forward
                    sF = vgg(styleV)
                    cF = vgg(contentV)

                    if(cfg.TRANS.LAYER == 'r41'):
                        feature, transmatrix = matrix(cF[cfg.TRANS.LAYER], sF[cfg.TRANS.LAYER])
                    else:
                        feature, transmatrix = matrix(cF, sF)

                    transfer = dec(feature)
                    transfer = transfer.clamp(0, 1)

                    if cfg.TRANS.VERBOSE:
                        logging.info('trasnfer took %3.2f seconds' % (time.time() -t1))

                    vutils.save_image(transfer, stylized_image_file,
                                      normalize=True, scale_each=True, nrow=cfg.TRANS.BATCHSIZE)
                    torch.cuda.empty_cache()

                    try:
                        with open(stylized_image_file, 'rb') as f:
                            img = Image.open(f)
                        break
                    except:
                        logging.info('Image broken -> try again')
                        continue

                if cfg.TRANS.VERBOSE:
                    logging.info('Transferred image %s style_id %d' % (contentName, sj+1))


