FROM continuumio/miniconda3

RUN conda update --yes -c conda-forge --all
RUN conda install --yes -c conda-forge rios fiona affine shapely rasterio pyproj proj4 blas kealib numpy dill requests scikit-learn bottleneck

ARG manifest
LABEL "up42_manifest"=$manifest

WORKDIR /block
COPY . /block/

CMD ["python", "/block/run.py"]