from networks.vgg16 import VGG16, VGG16BN
from networks.alexnet import ALEXNET

def init(cfg):
    """ Network initialization """

    network_type = cfg.RET.NETWORK.TYPE
    if network_type == 'alexnet':
        featureExtractor = ALEXNET(cfg)
    elif network_type in ['vgg16', 'vgg16bn']:
        featureExtractor = VGG16BN(cfg) if ('bn' in network_type) else VGG16(cfg)
    else:
        raise ValueError('Unknown network %s' % network_type)
    return featureExtractor
