### general setup: dataprepper.py


Dataset as of 2024-07-20 (260.000 rows)


| Description | Memory usage | CPU usage (time needed) |
| --- | ---:| ---:|
| loaded directly from CSV into pandas object    |    27.1 MB |       n.a. |
| extended by their norm xyzH/xyzL-Values        | +  33.6 MB |       n.a. |
| (!!) IGNORED FOR THIS TEST: resampling (!!)    |too much GB | multiple s |
| calculating body_df or gravity_df (same thing) | +  33.6 MB |    81.8 ms |
| merging together: baseline_df = body+gravity   | +  62.2 MB |    16.3 ms | 
| baseline to derivative                         | +  65.2 MB |    69.3 ms |
| merging together: intermediate = baseline+deriv| + 128.5 MB |    60.2 ms |



for each group of (hundrets) the following process is initiated. this process could be paralellized(!), but isn't yet


| Description | Memory usage | CPU usage (time needed) |
| --- | ---:| ---:|
| slicing single group out of dataset            |   253.9 KB |   962.3 µs |
| calculating mean of single group   (pandas)    |    n.a.    |   318.7 µs |
| calculating stddev of single group (pandas)    |    n.a.    |   397.1 µs |
| calculating mad of single group                |    n.a.    |  5785.4 µs |
| calculating min of single group    (pandas)    |    n.a.    |   270.1 µs |
| calculating max of single group    (pandas)    |    n.a.    |   282.1 µs |
| calculating signal magnitude (sma)             |    n.a.    |  8383.7 µs |
| calculating iqr of single group                |    n.a.    |  5915.4 µs |
| calculating entropy of single group            |    n.a.    | 14049.0 µs |
| calculating energy of single group             |    n.a.    |  2146.6 µs |
| calculating 8 FFT buckets of single group      |      ~8 KB |  7755.0 µs |
| merging all subcalculations together           |   ~17.0 KB |   125.2 µs |


Theoretical mathematical operations needed:

N = number of rows in a single group
| Math term | Big O|
| -- | -- |
| `mean   = N*add + 1*div`                                    | N  |
| `stddev = mean + N*sub + N*square + N*add + 1*sqrt`         | 4N |
| `mad    = mean + N*sub + N*abs + 1*div`                     | 3N | 
| `min    = N*comp`                                           | N  |
| `max    = N*comp`                                           | N  |
| `sma` simpson formula | tbd |
| `iqr` quantiles | tbd |
| `entropy=` | tbd |
| `energy =` | tbd |
| `fft    = `| k* N*log(N) |