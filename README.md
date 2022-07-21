# mousereader
 Python Package for reading MOUSE result files. Requires DHI MIKE URBAN installation.

<b>To install:</b>

```
python -m pip install https://github.com/enielsen93/mousereader/tarball/master
```

## Example:
```
files = ["C:\Offline\VOR_Status\VOR_Status_CDS100_CDS100.CRF",
            "C:\Offline\VOR_Status\VOR_Status_CDS20_CDS20.CRF",
            "C:\Offline\VOR_Status\VOR_Status_CDS5_CDS5.CRF",
            "C:\Offline\VOR_Status\VOR_Status_CDS10_CDS10.CRF"]

import matplotlib.pyplot as plt

plt.figure()
for file in files:
    mouse_result = MouseResult(file, r"Vinkel")
    plt.step(mouse_result.dataframe.index, mouse_result.dataframe.values, label = file)
plt.legend()
plt.show()
```
