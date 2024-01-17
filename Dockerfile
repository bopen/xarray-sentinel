FROM continuumio/miniconda3

WORKDIR /src/xarray-sentinel

COPY environment.yml /src/xarray-sentinel/

RUN conda install -c conda-forge gcc python=3.11 \
    && conda env update -n base -f environment.yml

COPY . /src/xarray-sentinel

RUN pip install --no-deps -e .
