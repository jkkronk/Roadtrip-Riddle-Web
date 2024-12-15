from staticmap import StaticMap, CircleMarker
from PIL import Image
from multiprocessing import Pool
from functools import partial

def create_single_map(coordinate_data, output_prefix, width, height, tile_url, zoom):
    """
    Helper function to create a single map for parallel processing
    """
    i, (lat, lon, bearing) = coordinate_data
    
    # Adjust zoom level based on image index
    adjusted_zoom = zoom - (i // 250)  # Decrease zoom by 1 for each 100 images
    
    # Create a static map centered on the given coordinates
    m = StaticMap(width*2, height*2, url_template=tile_url)
    
    # Add a marker at the given coordinate
    marker = CircleMarker((lon, lat), 'blue', 24)
    m.add_marker(marker)
    
    # Render the map with adjusted zoom
    image = m.render(zoom=adjusted_zoom)
    
    # Apply rotation if bearing is set
    if bearing != 0:
        image = image.rotate(bearing, expand=True)
    
    # Crop the image
    image = image.crop((
        (image.width - width) // 2,
        (image.height - height) // 2,
        (image.width + width) // 2,
        (image.height + height) // 2
    ))
    
    filename = f"{output_prefix}{i}.png"
    image.save(filename)

def save_maps_for_coordinates(coordinates, 
                            output_prefix="map_", 
                            width=600, height=600, 
                            tile_url='http://a.tile.osm.org/{z}/{x}/{y}.png',
                            zoom=12):
    """
    Parallel version of map creation using multiprocessing
    """
    # Create a partial function with all parameters except the coordinate data
    process_map = partial(create_single_map, 
                         output_prefix=output_prefix,
                         width=width, 
                         height=height,
                         tile_url=tile_url,
                         zoom=zoom)
    
    # Create enumerated coordinate list for processing
    coordinate_data = list(enumerate(coordinates))
    
    # Use multiprocessing to create maps in parallel
    with Pool(processes=2) as pool:
        pool.map(process_map, coordinate_data)

