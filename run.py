"""
JRSRP Fractional Cover processing block.
Input is Sentinel 2 L2A data from Sentinel-Hub
Output is a 3 band fractiona cover image
Peter Scarth 2019-08-05 

"""
import json
import shutil
import os
import pathlib
import dill
from sklearn.svm import SVR
import numpy as np
from rios import applier

AOICLIPPED = "up42.data.aoiclipped"

def ensure_data_directories_exist():
    """
    This method checks input and output directories for data flow
    """
    pathlib.Path('/tmp/input/').mkdir(parents=True, exist_ok=True)
    pathlib.Path('/tmp/output/').mkdir(parents=True, exist_ok=True)


def load_input():
    """
    Load the input data from the local filesystem
    """
    if os.path.exists("/tmp/input/data.json"):
      with open("/tmp/input/data.json") as fp:
          return json.loads(fp.read())
    else:
        return []

def write_output(result):
    """
    Write the result data to the /tmp/output directory.
    If you are storing image data, you would need to then copy that data into this directory as well.
    """
    with open("/tmp/output/data.json", "w") as fp:
        fp.write(json.dumps(result))
 
def load_estimators():
    """
    Reads the ML fractional cover estimators 
    """
    with open('svmPipelines', 'rb') as input:
        return dill.load(input)

"""
Logit transforms adapted to account for 0 and 1
""" 
def logit(p):
    q = p * 0.98 + 0.01
    return np.log(q) - np.log(1 - q)

def expit(q):
    p =  np.exp(q) / (1 + np.exp(q))
    return (p - 0.01) / 0.98

def unmixfc(info,inputs,outputs,otherargs):
    """
    JRSRP SVR Fractional Cover Estimator
    Adapted to run on UP42
    """
    # Pull out the sentinel bands
    # See https://docs.sentinel-hub.com/api/latest/#/API/data/Sentinel-2-L2A for the Sentinel-Hub bands
    nbar = inputs.nbar[[1,2,3,7,10,11]]
    # Get the shape of the input array
    inshape = nbar.shape
    # Flatten and convert to floating point reflectance
    # See below for scaling:
    # https://www.sentinel-hub.com/faq/how-are-values-calculated-within-sentinel-hub-and-how-are-they-returned-output
    nbar = np.reshape(nbar,(inshape[0],-1)) / 65535.0
    # Convert Sentinel 2 to Landsat ETM using Flood coefficients
    nbar = np.transpose(np.transpose(nbar) * 
                        np.array([0.9551, 1.0582, 0.9871, 1.0187, 0.9528, 0.9688]) + 
                        np.array([-0.0022, 0.0031, 0.0064, 0.012, 0.0079, -0.0042]))
    # Compute Indicies
    ndvi = (nbar[3]-nbar[2])/(nbar[3]+nbar[2] + np.finfo('float32').eps)
    burn = (nbar[3]-nbar[5])/(nbar[3]+nbar[5] + np.finfo('float32').eps)
    ndwi = (nbar[3]-nbar[4])/(nbar[3]+nbar[4] + np.finfo('float32').eps)
    # Compute Green
    refDataGreen = np.transpose(np.append(nbar[1:],[ndvi,burn,ndwi],axis=0))
    green = expit(otherargs.greenEstimator.predict(refDataGreen))
    # Compute non-green
    refDataNonGreen = np.append(refDataGreen,np.transpose([green]),axis=1)
    nongreen = expit(otherargs.nonGreenEstimator.predict(refDataNonGreen))
    # Compute Bare
    refDataBare = np.append(refDataNonGreen,np.transpose([nongreen]),axis=1)
    bare = expit(otherargs.bareEstimator.predict(refDataBare))
    # Scale Fractions
    totalSum = bare + green + nongreen + np.finfo('float32').eps
    # Scale Output
    outputFC = np.round(100 + 100 * np.array([bare,green,nongreen]) / totalSum,0)
    # Mask out of range data
    outputFC[:,nbar[0] < 0.001] = 0
    # Mask NDVI Threshold
    outputFC[:,ndvi < 0.01] = 0
    # Mask Bright Threshold
    #outputFC[:,nbar.min(axis=0) > 0.24] = 0

    # Reshape the output
    outputFC = np.reshape(outputFC,(3,inshape[1],inshape[2]))
    # Write the FC Output
    outputs.fc =  outputFC.astype(np.uint8)

def run(data):
    # Load the machine learning estimators
    (greenEstimator,nonGreenEstimator,bareEstimator) = load_estimators()
    # Read in the FC ML Models
    otherargs = applier.OtherInputs()
    otherargs.greenEstimator = greenEstimator
    otherargs.nonGreenEstimator = nonGreenEstimator
    otherargs.bareEstimator = bareEstimator
    # Setup file name associations
    infiles = applier.FilenameAssociations()
    outfiles = applier.FilenameAssociations()

    # Loop for each image
    for feature in data.get("features"):
        print("Found GeoJSON feature:\n%s" % feature)
        # Find the filename
        rel_image_path = feature["properties"].get(AOICLIPPED)
        print("Processing %s" % rel_image_path)
        infiles.nbar = "/tmp/input/%s" % rel_image_path
        outfiles.fc = os.path.splitext("/tmp/output/%s" % rel_image_path)[0] + "_fc.tif"
        # Set up processing controls
        controls = applier.ApplierControls()
        controls.setStatsIgnore(0)
        controls.setOutputDriverName("GTIFF")
        controls.setCreationOptions(["COMPRESS=DEFLATE",
                                     "ZLEVEL=9",
                                     "BIGTIFF=YES",
                                     "TILED=YES",
                                     "INTERLEAVE=BAND",
                                     "NUM_THREADS=ALL_CPUS"])
        # Run the model
        applier.apply(unmixfc, infiles, outfiles, otherargs, controls=controls)
        print("Feature has an FC image at %s" % outfiles.fc)

    return data

# Main script entrypoint
if __name__ == "__main__":
    ensure_data_directories_exist()
    load_estimators()
    data = load_input()
    result = run(data)
    write_output(result)
