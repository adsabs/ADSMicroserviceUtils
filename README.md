[![Build Status](https://travis-ci.org/adsabs/ADSMicroserviceUtils.svg?branch=master)](https://travis-ci.org/adsabs/ADSMicroserviceUtils)
[![Coverage Status](https://coveralls.io/repos/github/adsabs/ADSMicroserviceUtils/badge.svg?branch=master)](https://coveralls.io/github/adsabs/ADSMicroserviceUtils?branch=master)

# ADSPipelineUtils
Set of common libraries used by ADS microservices.

Class ADSFlask is to be used by all the microservice applications, where logging is setup automatically. 
Note that if your microservice application requires logging to stdout in addition to the log file include

    LOG_STDOUT = True

in your microservice's config.py.
