""" Module for setting up statistical models
"""

import pylab as pl
import pymc as mc

# model goes here
def bad_model(X):
    """ Results in a matrix with shape matching X, but all rows sum to 1"""
    N, T, J = X.shape
    Y = pl.zeros_like(X)
    for t in range(T):
        Y[:,t,:] = X[:,t,:] / pl.outer(pl.array(X[:,t,:]).sum(axis=1), pl.ones(J))
    return Y.view(pl.recarray) 

def latent_simplex(X): # TODO: change to more appropriate name latent_simplex
    """ TODO: describe this function"""
    N, T, J = X.shape

    alpha = []
    for t in range(T):
        alpha_t = []
        for j in range(J):
            mu_alpha_tj = pl.mean(X[:,t,j]) / pl.mean(X[:,t,:], 0).sum()
            alpha_t.append(mc.Normal('alpha_%d_%d'%(t,j), mu=0., tau=1., value=pl.log(mu_alpha_tj)))
        alpha.append(alpha_t)

    @mc.deterministic
    def pi(alpha=alpha):
        pi = pl.zeros((T, J))
        for t in range(T):
            pi[t] = pl.reshape(pl.exp(alpha[t]), J) / pl.sum(pl.exp(alpha[t]))
        return pi

    beta = mc.Normal('beta', mu=0., tau=.1**-2, value=pl.zeros_like(pi.value), doc='bias term')

    sigma = [[mc.Normal('sigma_%d_%d'%(t,j), mu=X[:,t,j].std(), tau=.01**-2,
                      value=X[:,t,j].std()) for j in range(J)] for t in range(T)]
        
    @mc.observed
    def X_obs(pi=pi, beta=beta, sigma=sigma, value=X):
        logp = 0.
        for n in range(N):
            logp += mc.normal_like(value[n,:,:], mu=pi, tau=pl.array(sigma)**-2)
        return logp

    # old X_obs liklihood code
    # TODO: compare this mixture model likelihood to the simpler likelihood abover
        logp = pl.zeros(N)
        for n in range(N):
            logp[n] = mc.normal_like(pl.array(value[n]).ravel(),
                                     pl.array(pi).ravel(),
                                     pl.array(sigma).ravel()**-2)
        return mc.flib.logsum(logp - pl.log(N))
    
    return vars()

def fit_latent_simplex(X, iter=1000, burn=500, thin=5): 
    vars = latent_simplex(X)

    m = mc.MAP([vars['alpha'], vars['beta'], vars['X_obs']])
    m.fit(method='fmin_powell', verbose=1)
    print vars['pi'].value

    for em in range(2):
        m = mc.MAP([vars['alpha'],vars['beta'], vars['X_obs']])
        m.fit(method='fmin_powell', verbose=1)
        print vars['pi'].value

        m = mc.MAP([vars['sigma'], vars['X_obs']])
        m.fit(method='fmin_powell', verbose=1)
        print [['%.2f'%sigma_tj.value for sigma_tj in sigma_t] for sigma_t in vars['sigma']]
    
    m = mc.MCMC(vars)

    for alpha_t, sigma_t in zip(m.alpha, m.sigma):
        m.use_step_method(mc.AdaptiveMetropolis, alpha_t)
        #m.use_step_method(mc.AdaptiveMetropolis, sigma_t)
    m.use_step_method(mc.AdaptiveMetropolis, m.beta)

    m.sample(iter, burn, thin, verbose=1)
    pi = m.pi.trace()

    print 'mean: ', pl.floor(m.pi.stats()['mean']*100.+.5)/100.
    print 'ui:\n', pl.floor(m.pi.stats()['95% HPD interval']*100.+.5)/100.
    #acorr5 = pl.dot((pi - pi.mean(0))[:-5].T, (pi - pi.mean(0))[5:]) / pl.dot((pi - pi.mean(0))[:].T, (pi - pi.mean(0))[:])
    #print 'acorrs:', pl.diag(pl.floor(acorr5*1000.+.5)/1000.)

    return m, pi.view(pl.recarray)

def pretty_array(X, digits):
    return str(X)

