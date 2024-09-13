import numpy as np
from scipy.interpolate import splprep, splev
import vtk

class ChromosomeSpline:
    
    def __init__(self, control_points, t, real_id, smooth, num_points, spacing_z, spacing_y, spacing_x):
        self.control_points = control_points
        self.fitted_path = self.fit_spline(smooth, num_points)
        self.actor = None
        self.t = t
        self.centromere_index = 0
        self.arm_1 = 0
        self.arm_2 = 0
        self.id = real_id
        self.spacing_z = spacing_z
        self.spacing_y = spacing_y
        self.spacing_x = spacing_x

    ###################################################################

    def fit_spline(self, smooth, num_points):
        
        points = np.array(self.control_points)
        tck, u = splprep(points.T, s = smooth)
        
        # Evaluate the spline and measure its length
        u_new = np.linspace(u.min(), u.max(), num_points)
        spline_points = np.array(splev(u_new, tck)).T

        return spline_points

    ###################################################################

    def build_actor(self):       

        # Converting fitted spline points to VTK Points
        vtkPoints = vtk.vtkPoints()
        for point in self.fitted_path:
            vtkPoints.InsertNextPoint(point.tolist())

        # Create a PolyLine which represents the fitted spline
        polyline = vtk.vtkPolyLine()
        polyline.GetPointIds().SetNumberOfIds(len(self.fitted_path))
        for i in range(len(self.fitted_path)):
            polyline.GetPointIds().SetId(i, i)

        # Create a cell array to store the lines in and add the lines to it
        cells = vtk.vtkCellArray()
        cells.InsertNextCell(polyline)

        # Create a PolyData to store everything in
        polyData = vtk.vtkPolyData()

        # Add the points and lines to the dataset
        polyData.SetPoints(vtkPoints)
        polyData.SetLines(cells)

        # Use a tube filter to plot the line as a series of tubes, giving it thickness
        tubeFilter = vtk.vtkTubeFilter()
        tubeFilter.SetInputData(polyData)
        tubeFilter.SetRadius(0.3)  # Set the radius of the tubes
        tubeFilter.SetNumberOfSides(8)  # Set the number of sides for the tubes
        tubeFilter.Update()

        # Create a mapper and actor
        mapper = vtk.vtkPolyDataMapper()
        mapper.SetInputConnection(tubeFilter.GetOutputPort())

        actor = vtk.vtkActor()
        actor.SetMapper(mapper)
        actor.GetProperty().SetColor(1, 0, 0)  # Set spline color to red

        self.actor = actor

        return actor
        
    ###################################################################

    def indicate_centromere(self, point):

        # Find the index of the spline point closest to point
        min_distance = np.Inf
        centromere_index = 0
        for i, p in enumerate(self.fitted_path):
            current_distance = np.linalg.norm(np.array(point) - np.array(p))

            if current_distance < min_distance:
                min_distance = current_distance
                centromere_index = i

        self.centromere_index = centromere_index

    ###################################################################

    def measure_arms(self):

        arm_1 = 0
        arm_2 = 0

        for i in range(len(self.fitted_path) - 1):
            current_point = np.array(self.fitted_path[i])
            next_point = np.array(self.fitted_path[i + 1])

            if i < self.centromere_index:
                arm_1 += np.linalg.norm(current_point - next_point)
            else:
                arm_2 += np.linalg.norm(current_point - next_point)

        self.arm_1 = arm_1
        self.arm_2 = arm_2

        return arm_1, arm_2

    ###################################################################

    def save_to_file(self, filename):

        # Adjust by the scaling
        scaled_path = []
        for p in self.fitted_path:
            z, y, x = p
            scaled_path.append([z / self.spacing_z, y / self.spacing_y, x / self.spacing_x])
            
        np.savetxt(filename, np.array(scaled_path))

        with open(filename, "a") as f:
            
            # append the ID
            f.write(str("id") + " " + str(self.id) + "\n")

            # append the time point
            f.write(str("time") + " " + str(self.t) + "\n")
            
            # append the centromere point            
            f.write(str("centromere") + " " + str(self.centromere_index))
            
                
