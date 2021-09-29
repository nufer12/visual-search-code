import os
import os.path as osp
import numpy as np
from PIL import Image

from src.utils import check_dir


def get_img_pad_org(image_size, cfg):
    """ How much to pad in the original image space """
    img_pad_org = cfg.RET.IMG.PADDING / cfg.RET.IMG.MINSIZE * np.min(image_size)
    return img_pad_org


def get_image_sizes(img_path, imagelist, cfg):
    """ Get image size of all images """
    # - get image sizes
    image_sizes = [Image.open(osp.join(img_path, f)).size for f in imagelist]
    image_sizes = np.array([np.array([s[1], s[0]]) for s in image_sizes])  # size different order, i.e. [w,h]
    # - adjust based on padding
    img_pad_orgs = np.apply_along_axis(lambda x: get_img_pad_org(x, cfg), 1, image_sizes).reshape(-1, 1)
    image_sizes_pad = image_sizes + 2 * np.tile(img_pad_orgs, [1, 2])
    return image_sizes, image_sizes_pad


def init_dataset_interface(cfg):
    """ Initialize dataset for interface """
    dataset_name = cfg.DATASET_NAME
    img_ext = '.jpg'
    img_path = check_dir(osp.join(cfg.DATA_DIR, 'images'))
    imagelist = os.listdir(img_path)
    images_ret = list(range(len(imagelist)))
    imagesizes, imagesizes_pad = get_image_sizes(img_path, imagelist, cfg)
    dataset = dict({'img_ext': img_ext,
                    'imagelist': imagelist,
                    'imagesizes': imagesizes,
                    'imagesizes_pad': imagesizes_pad,
                    'images_ret': images_ret,
                    'images_qu': [],
                    'img_path': img_path,
                    'imgAug_path': '',
                    'anno_file_qu': '',
                    'anno_file_ret': '',
                    'name': dataset_name,
                    'nummaxlabel': 0})
    return dataset

