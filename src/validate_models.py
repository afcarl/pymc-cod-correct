import pymc as mc 
import pylab as pl 
import os
import subprocess
import csv

import data
import graphics
import models 
reload(models)

def calc_coverage(true_cf, preds):
    """
    Calculates the 95% hpd region for each cause from the provided model output; Returns an array 
    the same length as true_cf which contains 1 for each cause that is included in the 95% hpd 
    region and 0 elsewhere.
    """
    
    J = len(true_cf)
    hpd = mc.utils.hpd(preds, 0.05)
    covered = [hpd[cause][0] < true_cf[cause] < hpd[cause][1] for cause in range(J)]
    return pl.array(covered)

def calc_quality_metrics(true_cf, preds): 
    """ 
    Calculate the CSMF accuracy, aboslute error, and relative error for the 
    provided true and predicted CSMFs.
    """
    
    pred_cf = pl.array(preds.mean(0))
    true_cf = pl.array(true_cf)
    
    csmf_accuracy = 1. - pl.sum(pl.absolute(pred_cf - true_cf)) / (2*(1-min(true_cf))) 
    abs_err = pl.absolute(pred_cf-true_cf)
    rel_err = pl.absolute(pred_cf - true_cf)/true_cf
    coverage = calc_coverage(true_cf, preds)
    all = pl.np.core.records.fromarrays([abs_err, rel_err, pl.ones(len(pred_cf))*csmf_accuracy, coverage], names=['abs_err','rel_err','csmf_accuracy','coverage'])
    return all
    
def validate_once(true_cf = pl.ones(3)/3.0, true_std = 0.01*pl.ones(3), save=False, dir='', i=0):
    """
    Generate a set of simulated estimates for the provided true cause fractions; Fit the bad model and 
    the latent dirichlet model to this simulated data and calculate quality metrics. 
    """ 
    
    # generate simulation data
    X = data.sim_data_for_validation(1000, true_cf, true_std)

    # fit bad model, calculate 95% HPD region and fit metrics 
    bad_model = models.bad_model(X)
    bad_model_metrics = calc_quality_metrics(true_cf, bad_model)
    
    # fit latent dirichlet model, calculate 95% HPD region and fit metrics 
    m, latent_dirichlet = models.fit_latent_dirichlet(X) # TODO: Need to find the appropriate settings here
    latent_dirichlet_metrics = calc_quality_metrics(true_cf, latent_dirichlet)

    # either write results to disk or return them 
    if save: 
        pl.rec2csv(bad_model_metrics, '%s/metrics_bad_model_%i.csv' % (dir, i)) 
        pl.rec2csv(latent_dirichlet_metrics, '%s/metrics_latent_dirichlet_%i.csv' % (dir, i))
    else: 
        return bad_model_metrics, latent_dirichlet_metrics

def combine_output(cause_count, model, dir, reps, save=False):
    """
    Combine output on absolute error, relative error, csmf_accuracy, and coverage from from
    multiple runs of validate_once. Either saves the output to the disk, or returns arays
    for each. 
    """

    abs_err = pl.zeros(cause_count, dtype='f').view(pl.recarray) 
    rel_err = pl.zeros(cause_count, dtype='f').view(pl.recarray)
    coverage = pl.zeros(cause_count, dtype='f').view(pl.recarray)
    csmf_accuracy = []
    for i in range(reps): 
        metrics = pl.csv2rec('%s/metrics_%s_%i.csv' % (dir, model, i))
        abs_err = pl.vstack((abs_err, metrics.abs_err))
        rel_err = pl.vstack((rel_err, metrics.rel_err))
        coverage = pl.vstack((coverage, metrics.coverage))
        csmf_accuracy.append(metrics.csmf_accuracy[0])
    abs_err = abs_err[1:,]
    rel_err = rel_err[1:,]
    coverage = coverage[1:,]
    csmf_accuracy = pl.array(csmf_accuracy).reshape(reps,1)
    
    mean_abs_err = abs_err.mean(0)
    median_abs_err =  pl.median(abs_err, 0)
    mean_rel_err = rel_err.mean(0)
    median_rel_err = pl.median(rel_err, 0)
    mean_csmf_accuracy = csmf_accuracy.mean(0)
    median_csmf_accuracy = pl.median(csmf_accuracy, 0)
    mean_coverage_bycause = coverage.mean(0)
    median_coverage_bycause = pl.median(coverage, 0)
    mean_coverage = pl.mean(coverage.mean(1))
    percent_total_coverage = pl.mean(coverage.mean(1)==1)

    all = pl.np.core.records.fromarrays([mean_abs_err, median_abs_err, mean_rel_err, median_rel_err, 
                                         pl.ones(cause_count)*mean_csmf_accuracy, pl.ones(cause_count)*median_csmf_accuracy, 
                                         mean_coverage_bycause, median_coverage_bycause, pl.ones(cause_count)*mean_coverage, 
                                         pl.ones(cause_count)*percent_total_coverage], 
                                        names=['mean_abs_err', 'median_abs_err', 
                                         'mean_rel_err', 'median_rel_err', 'mean_csmf_accuracy', 'median_csmf_accuracy', 
                                         'mean_covearge_bycause', 'median_coverage_bycause', 'mean_coverage', 
                                         'percent_total_coverage'])

    if save: 
        data.rec2csv_2d(abs_err, '%s/%s_abs_err.csv' % (dir, model))
        data.rec2csv_2d(rel_err, '%s/%s_rel_err.csv' % (dir, model))
        data.rec2csv_2d(coverage, '%s/%s_coverage.csv' % (dir, model))
        data.rec2csv_2d(pl.array(csmf_accuracy).reshape(reps,1), '%s/%s_csmf_accuracy.csv' % (dir, model))
        pl.rec2csv(all, '%s/%s_summary.csv' % (dir, model)) 
    else: 
        return summary, abs_err, rel_err, csmf_accuracy, coverage

def summarize_output(dir, model): 
    """
    Calculate summary measures of the quality metrics for a given model fit
    """
    
    abs_err = data.csv2array('%s/%s_abs_err.csv' % (dir, model))
    mean_abs_err = abs_err.mean(0)
    median_abs_err =  pl.median(abs_err, 0)

    rel_err = data.csv2array('%s/%s_rel_err.csv' % (dir, model))
    mean_rel_err = rel_err.mean(0)
    median_rel_err = pl.median(rel_err, 0)

    csmf_accuracy = data.csv2array('%s/%s_csmf_accuracy.csv' % (dir, model))
    mean_csmf_accuracy = csmf_accuracy.mean(0)
    median_csmf_accuracy = pl.median(csmf_accuracy, 0)

    coverage = data.csv2array('%s/%s_coverage.csv' % (dir, model))
    mean_coverage_bycause = coverage.mean(0)
    median_coverage_bycause = pl.median(coverage, 0)
    mean_coverage = pl.mean(coverage.mean(1))
    percent_total_coverage = pl.mean(coverage.mean(1)==1)
    
    all = [mean_abs_err, median_abs_err, mean_rel_err, median_rel_err, mean_csmf_accuracy, median_csmf_accuracy, mean_coverage_bycause, median_coverage_bycause, mean_coverage, percent_total_coverage]
    return all 
    # add ability to write or return this like other functions here 
    # does it make sense to do this?? it make more sense just to put this into the quality_metrics function in the first place and skip this step and the extra burden of 
    #   saving and retrieving from the J drive. 
    
def clean_up(model, dir, reps):
    """
    Delete temporary files produced when running validate_once multiple times.
    """
    
    for i in range(reps):
        os.remove('%s/metrics_%s_%i.csv' % (dir, model, i))

def run_all_sequentially(dir='../data', true_cf=[0.3, 0.3, 0.4], true_std=[0.01, 0.01, 0.01], reps=5): 
    """
    Runs validate_once multiple times (as sepcified by reps) for the given true_cf and 
    true_std. Combines the output and cleans up the temp files. This is all accomplished
    sequentially on the local machine. 
    """

    if os.path.exists(dir) == False: os.mkdir(dir)
    
    # repeatedly run validate_once and save output 
    for i in range(reps): 
        validate_once(true_cf, true_std, True, dir, i)

    # combine all output across repetitions 
    combine_output(len(true_cf), 'bad_model', dir, reps, True)
    combine_output(len(true_cf), 'latent_dirichlet', dir, reps, True)  
    
    # delete intermediate files 
    clean_up('bad_model', dir, reps)
    clean_up('latent_dirichlet', dir, reps)

def run_on_cluster(dir='../data', true_cf=[0.3, 0.3, 0.4], true_std=[0.01, 0.01, 0.01], reps=5, tag=''):
    """
    Runs validate_once multiple times (as specified by reps) for the given true_cf and 
    true_std. Combines the output and cleans up the temp files. This accomplished in 
    parallel on the cluster. This function requires that the files cluster_shell.sh 
    (which allows for submission of a job for each iteration), cluster_validate.py (which
    runs validate_once for each iteration), and cluster_validate_combine.py (which 
    runs combine_output all exist. The tag argument allows for adding a string to the job 
    names so that this function can be run multiple times simultaneously and not have 
    conflicts between jobs with the same name. 
    """
    
    if os.path.exists(dir) == False: os.mkdir(dir)

    # write true_cf and true_std to file
    truth = pl.np.core.records.fromarrays([true_cf, true_std], names=['true_cf', 'true_std'])
    pl.rec2csv(truth, '%s/truth.csv' % (dir))    
    
    # submit all individual jobs to retrieve true_cf and true_std and run validate_once
    all_names = [] 
    for i in range(reps): 
        name = 'cc%s_%i' % (tag, i)
        call = 'qsub -cwd -N %s cluster_shell.sh cluster_validate.py %i "%s"' % (name, i, dir)
        subprocess.call(call, shell=True)
        all_names.append(name)
    
    # submit job to run combine_output and clean_up 
    hold_string = '-hold_jid %s ' % ','.join(all_names)
    call = 'qsub -cwd %s -N cc%s_comb cluster_shell.sh cluster_validate_combine.py %i "%s"' % (hold_string, tag, reps, dir)
    subprocess.call(call, shell=True)  




