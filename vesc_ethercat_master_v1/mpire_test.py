from concurrent.futures import as_completed

from dask.distributed import progress
from tqdm import tqdm


import time


def time_consuming_function(x: int) -> int:
    time.sleep(1)   # Simulate that this function takes some time to complete
    return x


# Data which will be passed to the above function
data = range(100)


# Serial processing
results = [time_consuming_function(x) for x in tqdm(data)]

# multiprocessing
with Pool(processes=5) as pool:
    results = [x for x in tqdm(pool.imap(time_consuming_function, data),
                               total=len(data))]
    
# ProcessPoolExecutor
with ProcessPoolExecutor(max_workers=5) as pool:
    futures = [pool.submit(time_consuming_function, x) for x in data]
    results = [future.result() 
               for future in tqdm(as_completed(futures), total=len(futures))]

# Joblib
results = Parallel(n_jobs=5)(delayed(time_consuming_function)(x) for x in tqdm(data))

# Dask
client = Client(n_workers=5)
futures = [client.submit(time_consuming_function, x) for x in data]
progress(futures)
results = client.gather(futures)
client.close()

# Ray (from https://github.com/ray-project/ray/issues/5554)
ray.init(num_cpus=5)
remote_function = ray.remote(time_consuming_function)
def to_iterator(obj_ids):
    while obj_ids:
        done, obj_ids = ray.wait(obj_ids)
        yield ray.get(done[0])
obj_ids = [remote_function.remote(x) for x in data]
results = [x for x in tqdm(to_iterator(obj_ids), total=len(obj_ids))]
ray.shutdown()

# MPIRE
with WorkerPool(n_jobs=5) as pool:
    results = pool.map(time_consuming_function, data, progress_bar=True)