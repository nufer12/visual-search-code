import os.path as osp
from src.utils import create_dir


def roiDirname(cfg):
    rois_outputpath = create_dir(osp.join(cfg.OUTPUT_DIR, 'rois', 'iou_%3.2f_%s_%s' % (
        cfg.RET.EVALUATION.IOU_THRESH,
        cfg.RET.ROI.TYPE,
        '_'.join([str(i) for i in cfg.RET.ROI.PARAMETERS])
    )))
    return rois_outputpath


def roiFileName(cfg):
    fileName = '%s_max%d_decrease%d.h5' % (
        cfg.RET.ROI.TYPE,
        cfg.RET.DISCPROP.MAX,
        cfg.RET.DISCPROP.DECREASE
    )
    return fileName


def baseName(cfg):
    baseName = '%s_%s%d_%s_%s_%s_%s' % (cfg.RET.NETWORK.TYPE,
                                        cfg.RET.NETWORK.POOLING.TYPE,
                                        cfg.RET.NETWORK.POOLING.SIZE,
                                        cfg.RET.ROI.TYPE,
                                        '_'.join([str(i) for i in cfg.RET.ROI.PARAMETERS]),
                                        cfg.RET.STYLE_AGGTYPE,
                                        '_'.join([str(i) for i in cfg.RET.STYLE_IDS])
    )
    return baseName


def featpool1Filename(cfg):
    filename = 'featpool1_%s.h5' % (baseName(cfg))
    return filename


def featpool2Filename(cfg):
    filename = 'featpool2_%s.h5' % (baseName(cfg))
    return filename


def featred1Filename(cfg):
    filename = 'featred1_%s.pkl' % (baseName(cfg))
    return filename


def featredpool1Filename(cfg):
    filename = 'featredpool1_%s%d_%s.h5' % (cfg.RET.FEAT_REDUCT.TYPE,
                                            cfg.RET.FEAT_REDUCT.DIMENSION,
                                            baseName(cfg))
    return filename


def featredpool2Filename(cfg):
    filename = 'featredpool1_%s%d_%s.h5' % (cfg.RET.FEAT_REDUCT.TYPE,
                                            cfg.RET.FEAT_REDUCT.DIMENSION,
                                            baseName(cfg))
    return filename


def indexFilename(cfg):
    filename = 'index_%s_%s%d_%s.index' % (cfg.RET.FAISS.TYPE,
                                           cfg.RET.FEAT_REDUCT.TYPE,
                                           cfg.RET.FEAT_REDUCT.DIMENSION,
                                           baseName(cfg))
    return filename


def pqReconFilename(cfg):
    filename = 'pqRecon_%s_%s%d_%s.index' % (cfg.RET.FAISS.PQRECONTYPE,
                                             cfg.RET.FEAT_REDUCT.TYPE,
                                             cfg.RET.FEAT_REDUCT.DIMENSION,
                                             baseName(cfg))
    return filename


def pqReconh5Filename(cfg):
    filename = 'pqReconh5_%s_%s%d_%s.h5' % (cfg.RET.FAISS.PQRECONTYPE,
                                            cfg.RET.FEAT_REDUCT.TYPE,
                                            cfg.RET.FEAT_REDUCT.DIMENSION,
                                            baseName(cfg))
    return filename


def pqReconh5Filename_exp(cfg):
    if cfg.RET.SAVELOAD.INDEX_SAVE or cfg.RET.SAVELOAD.INDEX_LOAD:
        filename = pqReconh5Filename(cfg)
    else:
        filename = 'pqReconh5_%s.h5' % (cfg.EXP_NAME)
    return filename


def refinementh5Filename(cfg):
    filename = 'refinementh5_%s%d_%s.h5' % (cfg.RET.FEAT_REDUCT.TYPE,
                                            cfg.RET.FEAT_REDUCT.DIMENSION,
                                            baseName(cfg))
    return filename


def infovecFilename(cfg):
    filename = 'infovec_%s_%s%d_%s.h5' % (cfg.RET.FAISS.TYPE,
                                          cfg.RET.FEAT_REDUCT.TYPE,
                                          cfg.RET.FEAT_REDUCT.DIMENSION,
                                          baseName(cfg))
    return filename


def infovecimgFilename(cfg):
    filename = 'infovecimg_%s_%s%d_%s.h5' % (cfg.RET.FAISS.TYPE,
                                             cfg.RET.FEAT_REDUCT.TYPE,
                                             cfg.RET.FEAT_REDUCT.DIMENSION,
                                             baseName(cfg))
    return filename


def infovecimgrangeFilename(cfg):
    filename = 'infovecimgrange_%s_%s%d_%s.h5' % (cfg.RET.FAISS.TYPE,
                                                  cfg.RET.FEAT_REDUCT.TYPE,
                                                  cfg.RET.FEAT_REDUCT.DIMENSION,
                                                  baseName(cfg))
    return filename


def queryFilename(cfg):
    filename = 'queries_%s%d_%s.h5' % (cfg.RET.FEAT_REDUCT.TYPE,
                                       cfg.RET.FEAT_REDUCT.DIMENSION,
                                       baseName(cfg))
    return filename


def infovecquFilename(cfg):
    filename = 'infovecqu_%s%d_%s.h5' % (cfg.RET.FEAT_REDUCT.TYPE,
                                         cfg.RET.FEAT_REDUCT.DIMENSION,
                                         baseName(cfg))
    return filename


def proposalsFilename(cfg):
    filename = 'proposals_%s_max_%d.pkl' % (cfg.RET.ROI.TYPE, cfg.RET.DISCPROP.MAX)
    return filename

