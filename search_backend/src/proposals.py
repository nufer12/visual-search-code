import numpy as np

from src.utils import loadGT


def sample_prop_data(prop_data, dataset, num_images, num_patches, random_seed):

    """ Sample local patches """

    # - select subset of all proposals
    np.random.seed(random_seed)
    num_img_sample = min(num_images, len(dataset['images_ret']))
    img_sample = np.random.choice(dataset['images_ret'], num_img_sample, replace=False)
    info_vec = np.zeros([0, prop_data['info_vec'].shape[1]], dtype=np.float64)
    info_vec_img_range = np.zeros_like(prop_data['img_range'])
    for img_id, img_range in zip(img_sample, prop_data['img_range'][img_sample]):
        np.random.seed(random_seed)
        # - sample random patches
        info_vec_tmp = prop_data['info_vec'][int(img_range[0]):int(img_range[1]), :].copy()
        num_prop_sample = min(num_patches, info_vec_tmp.shape[0])
        sample_idx = np.random.choice(info_vec_tmp.shape[0], num_prop_sample, replace=False)
        # - remove sample
        sample_idx = np.arange(info_vec_tmp.shape[0])
        info_vec_img_range[img_id][0] = info_vec.shape[0]
        info_vec_img_range[img_id][1] = info_vec.shape[0] + sample_idx.shape[0]
        info_vec = np.concatenate([info_vec, info_vec_tmp[sample_idx, :]], axis=0)
        assert(sample_idx.shape[0] != 0)

    # - prepare output
    prop_data_sample = dict()
    prop_data_sample['info_vec'] = info_vec
    prop_data_sample['img_ids'] = list(set(info_vec[:, 0].astype(np.int)))
    prop_data_sample['img_range'] = info_vec_img_range
    prop_data_sample['info_vec_img'] = prop_data['info_vec_img'].copy()

    return prop_data_sample

