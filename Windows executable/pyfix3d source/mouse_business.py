# Mouse business
from pynput import mouse

class MouseBusiness:
    def __init__(self, visualizer_3d):
        self.visualizer_3d = visualizer_3d
        self.pressed = False
        self.current_lookat = [0, 0, 0]

    def on_move(self, x, y):

        self.visualizer_3d.drag = True
        """
        if self.visualizer_3d.raw_v is not None and self.pressed:
            phi, theta = self.visualizer_3d.get_rotation()
            self.visualizer_3d.raw_v.synchronize(phi, theta, self.visualizer_3d.t)
        """

    def on_click(self, x, y, button, pressed):

        if True: #try:
            self.current_lookat = self.visualizer_3d.v.get("lookat")
            if self.visualizer_3d.measure_mode == -1:
                self.visualizer_3d.update_selection_from_mouse()
                self.pressed = pressed

            if pressed == False:
                pass
                #self.visualizer_3d.check_update_camera(self.current_lookat)
                #self.visualizer_3d.unselect_out_of_time_points()
        else: #except Exception as e:
            with open ("error_log.txt", "a+") as f:
                f.write ("Error occurred in update selection upon click (>):\n")
                f.write (str(e) + "\n")
        
        
    def on_scroll(self, x, y, dx, dy):
        pass
