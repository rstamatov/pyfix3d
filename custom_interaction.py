import vtk
import numpy as np
from matplotlib.path import Path
from scipy.spatial import cKDTree

class CustomInteractorStyle(vtk.vtkInteractorStyleTrackballCamera):

    def __init__(self, visualizer_3d, parent = None):

        self.visualizer_3d = visualizer_3d
        
        self.AddObserver("LeftButtonPressEvent", self.leftButtonPressEvent)
        self.AddObserver("LeftButtonReleaseEvent", self.leftButtonReleaseEvent)
        self.AddObserver("MouseMoveEvent", self.mouseMoveEvent)
        
        self.ctrlPressed = False
        self.dragging = False
        self.startPos = None  # To store the start position of the drag
        self.endPos = None  # To store the end position of the drag

        self.cellLocator = vtk.vtkCellLocator()
        self.cellLocator.SetDataSet(self.visualizer_3d.imageData)
        self.cellLocator.BuildLocator()

        self.path = []  # To store the path of the drag
        self.polylineActor = vtk.vtkActor()
        self.polylineActor.GetProperty().SetColor(1.0, 1.0, 0.0)
        self.polylineActor.GetProperty().SetPointSize(6)
        self.polylineActor.GetProperty().SetRepresentationToPoints()
        
        self.polylineMapper = vtk.vtkPolyDataMapper()
        self.polylineData = vtk.vtkPolyData()  # This will hold the points and lines
        self.polylinePoints = vtk.vtkPoints()
        self.polylineLines = vtk.vtkCellArray()

        self.polylineData.SetPoints(self.polylinePoints)
        self.polylineData.SetLines(self.polylineLines)

        self.polylineMapper.SetInputData(self.polylineData)
        self.polylineActor.SetMapper(self.polylineMapper)

        self.visualizer_3d.renderer.AddActor(self.polylineActor)

    ##############################################################################################################################

    def leftButtonPressEvent(self, obj, event):
        
        
        self.ctrlPressed = self.GetInteractor().GetControlKey()
        if self.ctrlPressed:
            self.startPos = self.GetInteractor().GetEventPosition()
            self.dragging = True
            # Do not call OnLeftButtonDown to prevent camera rotation
        else:
            self.OnLeftButtonDown()

    ##############################################################################################################################

    def interpolatePoints(self, startPoint, endPoint, numPoints = 10):
        
        """Interpolate numPoints between startPoint and endPoint, inclusive of endpoints."""
        interpolatedPoints = []
        for i in range(numPoints + 1):
            alpha = i / float(numPoints)
            interpolatedPoint = [startPoint[j] + alpha * (endPoint[j] - startPoint[j]) for j in range(3)]
            interpolatedPoints.append(interpolatedPoint)
        return interpolatedPoints

    ##############################################################################################################################


    def leftButtonReleaseEvent(self, obj, event):
        
        
        if self.ctrlPressed and self.dragging:
            
            self.endPos = self.GetInteractor().GetEventPosition()
            self.markPointsWithinRectangle()
            self.dragging = False  # Reset dragging status
            self.clear_selection()
        else:
            self.OnLeftButtonUp()  # Handle normal release event

    ##############################################################################################################################

    def mouseMoveEvent(self, obj, event):
        
        
        if self.ctrlPressed and self.dragging and self.visualizer_3d.magic_wand:

            currentPos = self.GetInteractor().GetEventPosition()

            if currentPos is not None:
                self.path.append(currentPos)
                self.visualizePath()

            # Call self.OnMouseMove() if you also want to allow the normal mouse move behavior
        else:
            self.OnMouseMove()

    ##############################################################################################################################

    def clear_selection(self):
        
        # Clear the path
        self.path = []
        
        # Clear the contents of polylinePoints and polylineLines
        if self.polylinePoints:
            self.polylinePoints.Reset()
        if self.polylineLines:
            self.polylineLines.Reset()
        
        # Delete the contents explicitly to ensure they are cleared
        self.polylineData.Initialize()  # This reinitializes the polydata, effectively clearing it.

        self.polylineData.SetPoints(self.polylinePoints)
        self.polylineData.SetLines(self.polylineLines)

        self.polylineMapper.SetInputData(self.polylineData)

        # Ensure that any changes are reflected in the render window
        self.visualizer_3d.renderer.GetRenderWindow().Render()

    ##############################################################################################################################

    def visualizePath(self):

        if not self.visualizer_3d.magic_wand:
            return
        
        # Clear existing points and lines
        self.polylinePoints.Reset()
        self.polylineLines.Reset()

        self.polylineActor.GetProperty().SetPointSize(6)
        self.polylineActor.GetProperty().SetRepresentationToPoints()

        # Ensure there is at least one point to draw
        if len(self.path) < 2:
            return

        world_path = [self.screenToWorld(currentPos[0], currentPos[1]) for currentPos in self.path]

        # Convert the 2D screen points to 3D world coordinates, and store them for interpolation
        for idx in range(1, len(world_path)):
            prevPoint = list(world_path[idx - 1])
            currentPoint = list(world_path[idx])

            # Get interpolated points between prevPoint and currentPoint
            interpPoints = self.interpolatePoints(prevPoint, currentPoint, numPoints = 2)

            
            for interpIdx, interpPoint in enumerate(interpPoints):
                pointId = self.polylinePoints.InsertNextPoint(interpPoint)

                # For the first interpolated point, connect it to the previous segment
                # For other points, connect each to the previous interpolated point
                if idx > 1 or interpIdx > 0:
                    line = vtk.vtkLine()
                    line.GetPointIds().SetId(0, pointId - 1)  # Index of the previous point/interpolated point
                    line.GetPointIds().SetId(1, pointId)     # Index of the current interpolated point
                    self.polylineLines.InsertNextCell(line)

        # Notify the polyline data of the updated points and lines
        self.polylineData.Modified()

        # Update the mapper with the new polyline data
        self.polylineMapper.Update()

        # Refresh the render window to show the updated drawing
        self.visualizer_3d.renderer.GetRenderWindow().Render()

    ##############################################################################################################################

    def screenToWorld(self, x, y):
        
        renderer = self.visualizer_3d.renderer
        
        # Get the size of the render window
        renderWindow = renderer.GetRenderWindow()
        windowSize = renderWindow.GetSize()
        
        # Normalize the screen coordinates (0 to 1)
        normalizedX = x / windowSize[0]
        normalizedY = y / windowSize[1]
        
        # Adjust for the aspect ratio of the window
        aspectRatio = windowSize[0] / windowSize[1]
        
        # Get camera properties
        camera = renderer.GetActiveCamera()
        cameraPos = camera.GetPosition()
        cameraFp = camera.GetFocalPoint()
        cameraViewUp = camera.GetViewUp()
        
        # Calculate the view angle and depth of field based on camera settings
        viewAngle = camera.GetViewAngle()
        depthOfField = camera.GetDistance()
        
        # Calculate world coordinates here based on the camera position and the normalized screen coordinates
        # This example doesn't provide the exact maths as it depends on your specific use case and VTK's utilities
        # You may use vtkCoordinate for conversion, for example:
        
        # Create a vtkCoordinate object for conversion
        coordinate = vtk.vtkCoordinate()
        coordinate.SetCoordinateSystemToDisplay()
        coordinate.SetValue(x, y, 0) 
        
        # Convert to world coordinates
        worldPos = coordinate.GetComputedWorldValue(renderer)
        
        return worldPos

    ##############################################################################################################################
    
    def remove_overlapping_points(self, inside_points):
        # Convert list to a NumPy array for easier manipulation
        points_array = np.array(inside_points)
        
        camera = self.visualizer_3d.renderer.GetActiveCamera()
        view_angle = camera.GetViewAngle()  # In degrees
        depthOfField = camera.GetDistance()

        print ("View angle = ", view_angle)
        print ("Depth of field = ", depthOfField)
        
        # Adjust the threshold based on view angle or other zoom indicators
        # This is a simplified formula and might need adjustments
        threshold = 10.0 / (view_angle / 30.0)  # Example formula, adjust as necessary

        reduced_points = np.round(points_array / threshold) * threshold
        
        # Find unique rows (points) based on reduced resolution
        _, unique_indices = np.unique(reduced_points, axis=0, return_index=True)
        unique_points = points_array[unique_indices]
        
        return unique_points.tolist()

    ##############################################################################################################################

    def find_pixels_along_line(self, start, end):

        # Calculate differences
        dx = abs(end[0] - start[0])
        dy = abs(end[1] - start[1])
        dz = abs(end[2] - start[2])
        
        # Ensure we have at least one point for each step in the longest dimension
        num_points = 2 * int(max(dx, dy, dz) + 1)  # +1 ensures both endpoints are included
    
        # Generate a sequence of numbers from 0 to 1 with num_points
        t = np.linspace(0, 1, num_points)
        
        # Linear interpolation from start to end for each coordinate
        x = start[0] + (end[0] - start[0]) * t
        y = start[1] + (end[1] - start[1]) * t
        z = start[2] + (end[2] - start[2]) * t
        
        # Rounding to get the discrete coordinates
        return np.round(np.vstack([x, y, z]).T).astype(int)

    ##############################################################################################################################


    def markPointsWithinRectangle(self):

        if not self.visualizer_3d.magic_wand:
            return

        if len(self.visualizer_3d.selected_labels) == 0:
            self.visualizer_3d.backup = vtk.vtkImageData()
            self.visualizer_3d.backup.DeepCopy(self.visualizer_3d.imageDataObjects[self.visualizer_3d.t])

        # Ensure there is at least one point to draw
        if len(self.path) < 2:
            return

        # If the user has selected a source color, collect only the pixels matching it.
        if self.visualizer_3d.source_color > 0:
            source_object = self.visualizer_3d.source_color

        # Otherwise, try to guess which object they want - take the center of the selection and closest to the view
        else:
            source_object = self.find_centroid_object_id(self.path)

        axisSpacing = self.visualizer_3d.imageData.GetSpacing()
        picker = self.visualizer_3d.picker

        # Use the collected inside points from the path instead of a rectangle grid
        inside_points = self.collect_inside_points()
        inside_points = [self.screenToWorld(currentPos[0], currentPos[1]) for currentPos in inside_points]
        
        intersectedPoints = []
        vtk_array = self.visualizer_3d.imageDataObjects[self.visualizer_3d.t].GetPointData().GetScalars()

        for pickedPosition in inside_points:
                     
            rayStart = self.visualizer_3d.renderer.GetActiveCamera().GetPosition()
            rayEnd = pickedPosition


            rayDirection = np.subtract(rayEnd, rayStart)
            rayDirectionNormalized = rayDirection / np.linalg.norm(rayDirection)
            
            # Perform ray cast to find cells intersected by the ray
            cellIds = vtk.vtkIdList()
            extensionFactor = 1000
            rayStartExtended = pickedPosition - (rayDirectionNormalized * extensionFactor)
            rayEndExtended = pickedPosition + (rayDirectionNormalized * extensionFactor)

            """
            intersectedPoints = self.find_pixels_along_line(rayStartExtended, rayEndExtended)
            for i, point in enumerate(intersectedPoints):
                point = [point[d] / axisSpacing[d] for d in range(3)]
                intersectedPoints[i] = point


            """
            self.cellLocator.FindCellsAlongLine(rayStartExtended, rayEndExtended, 0.01, cellIds)
            
            # Processing the intersected cells
            numCells = cellIds.GetNumberOfIds()
            for i in range(numCells):
                cellId = cellIds.GetId(i)
                cell = self.visualizer_3d.imageDataObjects[self.visualizer_3d.t].GetCell(cellId)
                points = cell.GetPoints()
                for j in range(points.GetNumberOfPoints()):
                    point = points.GetPoint(j)
                    normalizedPoint = [point[d] / axisSpacing[d] for d in range(3)]
                    intersectedPoints.append(normalizedPoint)

                

        points_to_update = []

        
        for imageCoordinates in intersectedPoints:
            i, j, k = imageCoordinates
            pointId = self.visualizer_3d.imageData.ComputePointId((int(i), int(j), int(k)))
            points_to_update.append(pointId)

        points_to_update = np.unique(points_to_update)
        points_updated = []

        for id in points_to_update:

            if id < 0 or id >= vtk_array.GetNumberOfTuples():
                continue

            real_id = vtk_array.GetTuple1(id)
            if real_id == source_object:
                vtk_array.SetTuple1(id, 255)
                self.visualizer_3d.selected_labels.append(real_id)
                points_updated.append(id)

        self.visualizer_3d.selected_labels = list(np.unique(self.visualizer_3d.selected_labels))

        #self.visualizer_3d.selected_labels = list(np.unique(self.visualizer_3d.selected_labels))
        self.visualizer_3d.selected_voxels += list(points_updated)


        # Update imageData with new colors
        self.visualizer_3d.imageDataObjects[self.visualizer_3d.t].Modified()

        print (self.visualizer_3d.selected_labels + [255])

        self.visualizer_3d.init_surfaces(self.visualizer_3d.selected_labels + [255], self.visualizer_3d.t)
        self.visualizer_3d.set_current_image(self.visualizer_3d.t)

        #self.visualizer_3d.renderer.GetRenderWindow().Render()

    ##############################################################################################################################

    def collect_inside_points(self):
        print ("collect_inside_points")
        """
        Collect all 2D screen coordinates within a given path.
        
        Args:
        - path_points: A list of 2D tuples or numpy arrays representing the screen coordinates (x, y).
        
        Returns:
        - A list of 2D screen coordinates within the closed path.
        """

        path_points = self.path
        
        # Ensure the path is closed by connecting the last point to the first if they are not already connected.
        if path_points[0] != path_points[-1]:
            path_points.append(path_points[0])
        
        # Create a Path object (using matplotlib for simplicity, assuming straightforward paths without complicated self-intersections)
        path_obj = Path(path_points)
        
        # Get bounding box of the path to minimize the search area for interior points
        bbox = path_obj.get_extents()

        # Calculate the view angle and depth of field based on camera settings
        depthOfField = self.visualizer_3d.renderer.GetActiveCamera().GetDistance()
        resolution = 2 * (1 + int(800 / depthOfField)) #TODO - does this depend on the dimension of the input?
        
        # Generate a grid of points within the bounding box
        x, y = np.meshgrid(
            np.arange(bbox.xmin, bbox.xmax + 1, resolution), 
            np.arange(bbox.ymin, bbox.ymax + 1, resolution)
        )
        grid_points = np.vstack((x.flatten(), y.flatten())).T
        
        # Filter points to find which are inside the path
        inside_points = [point for point in grid_points if path_obj.contains_point(point)]
        
        # Filter points near the edge
        exclusion_distance = 1.0  # The exact value will need adjustment based on your coordinate system and requirements
        inside_points = self.filter_near_edge_points(inside_points, path_obj, exclusion_distance)
        
        return inside_points

    ##############################################################################################################################

    def filter_near_edge_points(self, inside_points, path_obj, exclusion_distance=1.0):
        # Convert the path object's vertices to a list of points
        path_points = [path_obj.vertices[i] for i in range(len(path_obj.vertices))]

        filtered_points = []
        for point in inside_points:
            # Calculate distance of the point from the path edge
            distance = self.calculate_distance_from_path_edge(point, path_points)
            if distance > exclusion_distance:
                filtered_points.append(point)
                
        return filtered_points

    ##############################################################################################################################

    def calculate_distance_from_path_edge(self, point, path_points):
        """
        Calculates the minimum distance from a point to the closest edge point of the path.
        
        Args:
        - point: The point for which we want to calculate the distance to the path.
        - path_points: A list of points that define the edges of the path.
        
        Returns:
        - The minimum distance from the point to the closest point on the path.
        """
        # Create a cKDTree object for efficient nearest neighbor searches
        tree = cKDTree(path_points)

        # Query the tree for the nearest neighbor to the 'point'
        distance, _ = tree.query(point)

        return distance

    ##############################################################################################################################

    def find_centroid_object_id(self, inside_points):
        """
        Finds the real_id of the object located at the geometric center
        of the points collected within the drawn region.
        """

        if len(inside_points) == 0:
            return None  # No points collected

        axisSpacing = self.visualizer_3d.imageData.GetSpacing()

        vtk_array = self.visualizer_3d.imageDataObjects[self.visualizer_3d.t].GetPointData().GetScalars()
        xi, yi = np.mean(inside_points, axis=0)
        
        clicked = None
        imageCoordinates = [0, 0, 0]
        
        if self.visualizer_3d.picker.Pick(xi, yi, 0, self.visualizer_3d.renderer):
            # Get the picked position in world coordinates
            pickedPosition = self.visualizer_3d.picker.GetPickPosition()
            #pickedPosition = [pickedPosition[d] / axisSpacing[d] for d in range(3)]            

            if pickedPosition is not None:
                self.visualizer_3d.imageData.TransformPhysicalPointToContinuousIndex(pickedPosition, imageCoordinates)
                picked_actor = self.visualizer_3d.picker.GetActor()

                print ("Pickable = ", picked_actor.GetPickable())
                try:
                    clicked = self.visualizer_3d.find_clicked_object(imageCoordinates)
                except Exception as e:
                    print (e)
                
        print (clicked)
        if clicked is not None:
            
            i, j, k = clicked
            pointId = self.visualizer_3d.imageData.ComputePointId((int(i), int(j), int(k)))
            real_id =  vtk_array.GetTuple1(pointId)
            print ("real id = ", real_id)

            if real_id == 0 or self.visualizer_3d.visible[real_id] == False:
                return 255
            else:
                return real_id
        else:
            return 255

    
