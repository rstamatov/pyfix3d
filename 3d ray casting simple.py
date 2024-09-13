def get_3d_coordinates_from_2d_shape(M, points):

    # Convert points to numpy array for efficient indexing
    points_array = np.array(points)
    y_coords, x_coords = points_array[:, 0], points_array[:, 1]

    # Directly index M using the points. This gives us a (Nz, Npoints) array where Npoints is len(points)
    indexed_values = M[:, y_coords, x_coords]

    # Find non-zero values in this indexed array
    non_zero_z, non_zero_points = np.nonzero(indexed_values)

    # Initialize a list to hold the coordinates of non-zero points
    optimized_non_zero_coordinates = []

    for z, point_index in zip(non_zero_z, non_zero_points):
        optimized_non_zero_coordinates.append((z, y_coords[point_index], x_coords[point_index]))

    return optimized_non_zero_coordinates
