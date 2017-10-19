import pytoml as toml
import numpy as np
import h5py
from collections import namedtuple
import os
import pdb
import logging
import six
import random
DimOrder = namedtuple('DimOrder', ('X', 'Y', 'Z'))
class bounds_generator(six_Iterator):
	def __init__(self,volume_shape,subvolume_shape,seed = 1):
		if len(volume_shape) != len(subvolume_shape):
		   raise ValueError('subvolume  dimension ({}) is not equal to '
                             'volume domension ({}). '
                             'This is currently unsupported.'.format(len(volume_shape), len(subvolume_shape)))
		for v_d,subv_d in zip(volume_shape,subvolume_shape):
			if v_d  <= subv_d:
			   raise ValueError('subvolume shape ({}) must smaller than '
                             'volum shape ({}).'.format(subvolume.shape,volume_shape))
	    self.volume_shape =volume_shape
		self.subvolume_shape =subvolume_shape:
		self.seed = seed
		random.seed(self.seed)
	@property
	def shape(self):
		return self.subvolume_shape
	def __iter__(self):
		return self
	def __next__(self):
		bounds = []
		for v_dim,sub_dim in zip(self.volume_shape,self.subvolume_shape): 
			start= random.randrange(0,v_dim-sub_dim)
			end  = start + sub_dim
			bounds.append((start,end))
		return bounds




class SubvolumeGenerator(six.Iterator):
    def __init__(self,volume,bounds_generator):
        self.volume =volume
        self.bounds_generator =bounds_generator
    @property
    def shape(self):
        return self.bounds_generator.shape
    def __iter__(self):
        return self
    def __next__(self):
        return self.volume.get_subvolume(six.next(self.bounds_generator))


class Volume(object):
    DIM = DimOrder(Z=0, Y=1, X=2)

    # def __init__(self, resolution, image_data=None, label_data=None, mask_data=None,
    # 	         gradX_data=None, gradY_data=None, gradZ_data=None, distTF_data =None,
    #              affinX1_data =None, affinX3_data  =None, affinX5_data = None,
    #              affinX7_data =None, affinX13_data =None, affinX20_data =None,
    #              affinY1_data =None, affinY3_data  =None, affinY5_data = None,
    #              affinY7_data =None, affinY13_data =None, affinY20_data =None,
    #              affinZ1_data =None, affinZ3_data  =None):
    #     self.resolution = resolution
    #     self.image_data = image_data
    #     self.label_data = label_data
    #     self.mask_data = mask_data
    #     self._mask_bounds = None

    #     self.gradZ_data = gradZ_data
    #     self.gradX_data = gradX_data
    #     self.gradY_data = gradY_data
    #     self.distTF_data = distTF_data



    #     self.affinX1_data =affinX1_data
    #     self.affinX3_data =affinX3_data 
    #     self.affinX5_data =affinX5_data
    #     self.affinX7_data =affineX7_data
    #     self.affinX13_data =affinX13_data
    #     self.affinX20_data =affinX20_data
        
    #     self.affinY1_data  =affinY1_data
    #     self.affinY3_data  =affinY3_data 
    #     self.affinY5_data  =affinY5_data
    #     self.affinY7_data  =affinY7_data 
    #     self.affinY13_data =affinY13_data
    #     self.affinY20_data =affinY20_data
        
    #     self.affinZ1_data =affinZ1_data
    #     self.affinZ3_data =affinZ3_data
    def __init__(self, resolution, data_dict):
        self.data_dict = data_dict
    def local_coord_to_world(self, a):
        return a

    def world_coord_to_local(self, a):
        return a

    def world_mat_to_local(self, m):
        return m

    @property
    def shape(self):
        return tuple(self.world_coord_to_local(np.array(self.image_data.shape)))

    def _get_downsample_from_resolution(self, resolution):
        resolution = np.asarray(resolution)
        downsample = np.log2(np.true_divide(resolution, self.resolution))
        if np.any(downsample < 0):
            raise ValueError('Requested resolution ({}) is higher than volume resolution ({}). '
                             'Upsampling is not supported.'.format(resolution, self.resolution))
        if not np.all(np.equal(np.mod(downsample, 1), 0)):
            raise ValueError('Requested resolution ({}) is not a power-of-2 downsample of '
                             'volume resolution ({}). '
                             'This is currently unsupported.'.format(resolution, self.resolution))
        return downsample.astype(np.int64)

    def downsample(self, resolution):
        downsample = self._get_downsample_from_resolution(resolution)
        if np.all(np.equal(downsample, 0)):
            return self
        return DownsampledVolume(self, downsample)

    def partition(self, partitioning, partition_index):
        if np.array_equal(partitioning, np.ones(3)) and np.array_equal(partition_index, np.zeros(3)):
            return self
        return PartitionedVolume(self, partitioning, partition_index)

    def sparse_wrapper(self, *args):
        return SparseWrappedVolume(self, *args)

    def subvolume_bounds_generator(self, shape=None, label_margin=None):
        return self.SubvolumeBoundsGenerator(self, shape, label_margin)

    def subvolume_generator(self, bounds_generator=None, **kwargs):
        if bounds_generator is None:
            if not kwargs:
                raise ValueError('Bounds generator arguments must be provided if no bounds generator is provided.')
            bounds_generator = self.subvolume_bounds_generator(**kwargs)
        return SubvolumeGenerator(self, bounds_generator)

    def get_subvolume(self, bounds):
        if bounds.start is None or bounds.stop is None:
            raise ValueError('This volume does not support sparse subvolume access.')


        def bounds2slice(bounds):
        	n_dim = len(bounds)
        	slices = [slice(None)]*n_dim
        	for i in range(n_dim):
        		slices[i] = slice(bounds[i][0],bounds[i][1])
        	return slices
        b_slices = bounds2slice(bounds)
        image_subvol = self.image_data[b_slices]
        if np.issubdtype(image_subvol.dtype, np.integer):
            image_subvol = image_subvol.astype(np.float32) / 256.0

        if self.label_data is not None:
        	label_subvol = self.label_data[b_slices]
        return Subvolume(image_subvol, label_mask, seed, label_id)

class HDF5Volume(Volume):
    """A volume backed by data views to HDF5 file arrays.

    Parameters
    ----------
    orig_file : str
        Filename of the HDF5 file to load.
    image_dataaset : str
        Full dataset path including groups to the raw image data array.
    label_dataset : str
        Full dataset path including groups to the object label data array.
    """
    @staticmethod
    def from_toml(filename):
        from keras.utils.data_utils import get_file
        volumes = {}
        with open(filename, 'rb') as fin:
        	ld = toml.load(fin).get('local_data',None)
        	data_dir =ld['data_dir']
        	if not os.path.exists(data_dir):
        		os.mkdir(data_dir)
        with open(filename, 'rb') as fin:
        	datasets = toml.load(fin).get('dataset', [])
        	print ('len is {}'.format(len(datasets)))
        	for dataset in datasets:
        		hdf5_file = dataset['hdf5_file']
        		filename = data_dir + '/'+ hdf5_file
        		if not os.path.exists(filename):
        			hdf5_file = get_file(hdf5_file, dataset['download_url'], 
        								md5_hash=dataset.get('download_md5', None), 
        								cache_subdir='', 
        								cache_dir=data_dir)
        		# image_dataset = dataset.get('image_dataset', None)
        		# label_dataset = dataset.get('label_dataset', None)
        		# mask_dataset = dataset.get('mask_dataset', None)
        		# mask_bounds = dataset.get('mask_bounds', None)
        		# resolution = dataset.get('resolution', None)
        		# gradX_dataset =dataset.get('gradX_dataset', None)
        		# gradY_dataset =dataset.get('gradY_dataset', None)
        		# gradZ_dataset =dataset.get('gradZ_dataset', None)
        		# distTF_dataset =dataset.get('distTF_dataset', None)

        		#all_data = dataset.get('data',None)
        		data_dict ={data['name']:data['path'] for data in dataset.get('data',None)}
        		# for data in in all_data:
        		#     data_dict[data['name']]=data['path']
        		volume = HDF5Volume(filename,
        			data_dict,
        			mask_bounds=mask_bounds)

        		# volume = HDF5Volume(filename,
        		# 	image_dataset,
        		# 	label_dataset,
        		# 	mask_dataset,
        		# 	gradX_dataset,
        		# 	gradY_dataset,
        		# 	gradZ_dataset,
        		# 	distTF_dataset,
        		# 	mask_bounds=mask_bounds)
        		# volumes[dataset['name']] = volume
                # If the volume configuration specifies an explicit resolution,
                # override any provided in the HDF5 itself.
                # if resolution:
                #     #logging.info('Overriding resolution for volume "%s"', dataset['name'])
                #     volume.resolution = np.array(resolution)
                #     volumes[dataset['name']] = volume
        return volumes

    @staticmethod
    def write_file(filename, **kwargs):
        h5file = h5py.File(filename, 'w')
        config = {'hdf5_file': filename}
        channels = ['image', 'label', 'mask','gradX','gradY','gradZ','distTF']
        default_datasets = {
            'image': 'volumes/raw',
            'label': 'volumes/labels/neuron_ids',
            'mask': 'volumes/labels/mask',
            'gradX': 'transformed_label/directionX',
            'gradY': 'transformed_label/directionY',
            'gradZ': 'transformed_label/directionZ',
            'distTF': 'transformed_label/distance',
            'affinX1': 'affinity_map/x1',
            'affinX3': 'affinity_map/x3',
            'affinX5': 'affinity_map/x5',
            'affinX7': 'affinity_map/x7',
            'affinX13': 'affinity_map/x13',
            'affinX20': 'affinity_map/x20',
            'affinY1': 'affinity_map/y1',
            'affinY3': 'affinity_map/y3',
            'affinY5': 'affinity_map/y5',
            'affinY7': 'affinity_map/y7',
            'affinY13': 'affinity_map/y13',
            'affinY20': 'affinity_map/y20',
            'affinZ1': 'affinity_map/z1',
            'affinZ3': 'affinity_map/z3',
        }
        for channel in channels:
            data = kwargs.get('{}_data'.format(channel), None)
            dataset_name = kwargs.get('{}_dataset'.format(channel), default_datasets[channel])
            if data is not None:
                dataset = h5file.create_dataset(dataset_name, data=data, dtype=data.dtype)
                #dataset.attrs['resolution'] = resolution
                config['{}_dataset'.format(channel)] = dataset_name

        h5file.close()

        return config

    def __init__(self, orig_file, image_dataset, label_dataset, mask_dataset, 
    	               gradX_dataset,gradY_dataset,gradZ_dataset,distTF_dataset,mask_bounds=None):
        logging.debug('Loading HDF5 file "{}"'.format(orig_file))
        self.file = h5py.File(orig_file, 'r')
        self.resolution = None
        self._mask_bounds = tuple(map(np.asarray, mask_bounds)) if mask_bounds is not None else None

        if image_dataset is None and label_dataset is None:
            raise ValueError('HDF5 volume must have either an image or label dataset: {}'.format(orig_file))

        if image_dataset is not None:
            self.image_data = self.file[image_dataset]
            if 'resolution' in self.file[image_dataset].attrs:
                self.resolution = np.array(self.file[image_dataset].attrs['resolution'])

        if label_dataset is not None:
            self.label_data = self.file[label_dataset]
            if 'resolution' in self.file[label_dataset].attrs:
                resolution = np.array(self.file[label_dataset].attrs['resolution'])
                if self.resolution is not None and not np.array_equal(self.resolution, resolution):
                    logging.warning('HDF5 image and label dataset resolutions differ in %s: %s, %s',
                                    orig_file, self.resolution, resolution)
                else:
                    self.resolution = resolution
        else:
            self.label_data = None

        if mask_dataset is not None:
            self.mask_data = self.file[mask_dataset]
        else:
            self.mask_data = None

        if image_dataset is None:
            self.image_data = np.full_like(self.label_data, np.NaN, dtype=np.float32)

        if self.resolution is None:
            self.resolution = np.ones(3)

        self.gradX_data = None if gradX_dataset is None else self.file[gradX_dataset]
        self.gradY_data = None if gradY_dataset is None else self.file[gradY_dataset]
        self.gradZ_data = None if gradZ_dataset is None else self.file[gradZ_dataset]
        self.distTF_data = None if distTF_dataset is None else self.file[distTF_dataset]


    def to_memory_volume(self):
        data = ['image_data', 'label_data', 'mask_data']
        data = {
                k: self.world_mat_to_local(getattr(self, k)[:])
                for k in data if getattr(self, k) is not None}
        return NdarrayVolume(self.world_coord_to_local(self.resolution), **data)
def run_test():
	print('read')
	file_name='../conf/cremi_datasets.toml'
	V = HDF5Volume.from_toml(file_name)

if __name__ == "__main__":
	run_test()