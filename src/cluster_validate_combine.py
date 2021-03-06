import os 
import sys
import pylab as pl 

import validate_models
reload(validate_models)
import data
reload(data)

reps = int(sys.argv[1])
dir = str(sys.argv[2])

true_cf = data.csv2array('%s/truth_cf.csv' % (dir))
T, J = true_cf.shape

validate_models.combine_output(J, T, 'bad_model', dir, reps, True)
validate_models.combine_output(J, T, 'latent_simplex', dir, reps, True)

validate_models.clean_up('bad_model', dir, reps)
validate_models.clean_up('latent_simplex', dir, reps)
os.remove('%s/truth.csv' %dir)
