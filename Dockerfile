#FROM continuumio/miniconda3
FROM  frolvlad/alpine-miniconda3
RUN conda update --yes -c conda-forge --all \
    && conda install --yes -c conda-forge rios fiona affine shapely rasterio pyproj proj4 numpy dill requests scikit-learn bottleneck poppler \
    && conda update --yes -c conda-forge --all \
    && conda clean -afy

ARG manifest
LABEL "up42_manifest"=$manifest

WORKDIR /block
COPY . /block/

CMD ["python", "/block/run.py"]