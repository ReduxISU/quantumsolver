FROM python:3.12-slim

RUN groupadd --system quantumsolver \
    && useradd --system --gid quantumsolver --no-create-home quantumsolver

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY --chown=quantumsolver:quantumsolver app/ app/
COPY --chown=quantumsolver:quantumsolver gunicorn.conf.py .
COPY --chown=quantumsolver:quantumsolver bernstein_vazirani_quantum.py bits.py deutsch_jozsa_quantum.py deutsch_quantum.py sat_quantum.py shors_quantum.py .

# gunicorn.conf.py binds a unix socket here in addition to TCP 27100
RUN mkdir -p /run/quantumsolver && chown quantumsolver:quantumsolver /run/quantumsolver

USER quantumsolver

EXPOSE 27100

CMD ["gunicorn", "--config", "gunicorn.conf.py", "app:app"]
