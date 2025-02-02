# Supress Warnings
import warnings
warnings.filterwarnings('ignore')

# Import common GIS tools
import numpy as np
import xarray as xr
import matplotlib.pyplot as plt
import rioxarray as rio
import rasterio
from matplotlib.cm import RdYlGn,jet,RdBu
import matplotlib.pyplot as plt

# Import Planetary Computer tools
import stackstac
import pystac_client
import planetary_computer
from odc.stac import stac_load

# global parameters
LOWER_LEFT = (40.75, -74.01)
UPPER_RIGHT = (40.88, -73.86)
BOUNDS = (LOWER_LEFT[1], LOWER_LEFT[0], UPPER_RIGHT[1], UPPER_RIGHT[0])
TIME_WINDOW = "2021-06-01/2021-09-01"
RESOLUTION = 10
SCALE = RESOLUTION / 111320.0 # degrees per pixel for crs=4326

# class to download data from planetary computer
class DownloadData:
    def __init__(self,filepath):
        self.filepath = filepath
        self.api_addr = "https://planetarycomputer.microsoft.com/api/stac/v1"
        self.num_items = None
        self.data = None

    def get_data(self):
        # connect
        stac = pystac_client.Client.open(self.api_addr)
        # search
        search = stac.search(
            bbox=BOUNDS,
            datetime=TIME_WINDOW,
            collections=["sentinel-2-l2a"],
            query={"eo:cloud_cover": {"lt": 30}},
        )
        # number of items used
        returned_items = list(search.get_items())
        self.num_items = len(returned_items)
        # Load data into xarray
        signed_items = [planetary_computer.sign(item).to_dict() for item in returned_items]
        # define resolution for final product
        self.data = stac_load(
            returned_items,
            bands = ["B01","B02","B03","B04","B05","B06","B07","B08","B8A","B11","B12"],
            crs="EPSG:4326",
            resolution=SCALE,
            chunks={"x":2048, "y":2048},
            dtype="uint16",
            patch_url=planetary_computer.sign,
            bbox=BOUNDS
        )
        return

    def save_xarray(self, filename):
        self.data.to_netcdf(self.filepath + filename)
        return  # save x array data

class PlotData:
    def __init__(self,filepath):
        self.filepath = filepath
        self.data = None

    def load_xarray(self, filename):
        self.data = xr.open_dataset(self.filepath + filename)
        return

    def plot_wrap_data(self,selection):
        plt.figure()
        plot_data = self.data[selection].to_array()
        # need to save this to an images folder
        plot_data.plot(
            col='time',
            col_wrap=4,
            robust=True,
            vmin=0,
            vmax=2500
        )
        plt.savefig(self.filepath + '/some_data.png', dpi=300)
        plt.close()
        return

    def plot_pane_data(self,selection,iselection):
        # reform this to print to folder
        fig, ax = plt.subplots(figsize=(6, 6))
        plot_data = self.data[[selection]].to_array()
        plot_data.isel(time=iselection).plot.imshow(robust=True,ax=ax,vmin=0,vmax=2500)
        ax.set_tilte("RGB Single Date: July 24, 2021")
        ax.axis('off')
        plt.show()
        return


# Class transforms x array data and saves as geotiff
class TransformData:
    def __init__(self,filepath):
        self.filepath = filepath
        self.data = None
        self.median = None
        self.ndvi_median = None
        self.ndbi_median = None
        self.ndwi_median = None

    def load_data(self,filename):
        self.data = xr.DataArray.load(self.filepath + filename)
        return

    def transform(self):
        self.median = self.data.median(dim="time").compute()
        self.ndvi_median = (self.median.B08 - self.median.B04)/(self.median.BO8 + self.median.B04)
        self.ndbi_median = (self.median.B11 - self.median.B08)/(self.median.B11 + self.median.B08)
        self.ndwi_median = (self.median.B03 - self.median.B08)/(self.median.B03 + self.median.B08)
        return

    def save_geotiff(self, filename, iselection):
        data_slice = self.data.isel(time=iselection)
        # calculate the dimensions of the file
        height = data_slice.dims["latitude"]
        width = data_slice.dims["longitude"]
        # define the CRS and bounding box
        gt = rasterio.transform.from_bounds(
            LOWER_LEFT[1],
            LOWER_LEFT[0],
            UPPER_RIGHT[1],
            UPPER_RIGHT[0],
            width,
            height
        )
        data_slice.rio.write_crs("epsg:4326", inplace=True)
        data_slice.rio.write_transform(transfrom=gt, inplace=True)
        # Create the GeoTIFF output
        with rasterio.open(
                filename,
                'w',
                driver='GTiff',
                width=width,
                height=height,
                crs='epsg:4326',
                transform=gt,
                count=4,
                compress='lzw',
                dtype='float64'
        ) as dst:
            dst.write(data_slice.B01, 1)
            dst.write(data_slice.B04, 2)
            dst.write(data_slice.B06, 3)
            dst.write(data_slice.B08, 4)
            dst.close()
        return

# and then call these functions
if __name__ == "__main__":
    # dd = DownloadData(filepath=r'C:/Users/HG749BX/PycharmProjects/UrbanHeatIndex/')
    # dd.get_data()
    # dd.save_xarray('download_01Feb2025.nc')
    # print(dd.num_items)
    #
    td = TransformData(filepath='rC:/Users/HG749BX/PycharmProjects/UrbanHeatIndex/')
    td.load_data('download_01Feb2025.nc')
    td.transform()
    td.save_geotiff(filename='geotiff_01Feb2025',iselection=7)





