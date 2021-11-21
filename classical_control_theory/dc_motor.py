# AUTOGENERATED! DO NOT EDIT! File to edit: 91_DC_motor.ipynb (unless otherwise specified).

__all__ = ['wrap', 'DCMotorParams', 'DCMotor', 'PID', 'Simulator', 'AnimateControlledPendulum']

# Cell
import numpy as np
import matplotlib
import matplotlib.pyplot as plt
from matplotlib import animation
from collections import defaultdict
import time

from .simple_pendulum import *

# Cell
def wrap(angle):
    "Wraps an angle between -pi and pi."
    return (angle + np.pi) % (2 * np.pi) - np.pi

# Cell
class DCMotorParams():
    def __init__(self,
                 J=0.01,
                 b=0.1,
                 K=0.01,
                 R=1,
                 L=0.5):
        self.J = J #     (J)     moment of inertia of the rotor     0.01 kg.m^2
        self.b = b #     (b)     motor viscous friction constant    0.1 N.m.s
        self.K = K #     (Ke)    electromotive force constant       0.01 V/rad/sec
                   #     (Kt)    motor torque constant              0.01 N.m/Amp
        self.R = R #     (R)     electric resistance                1 Ohm
        self.L = L #     (L)     electric inductance                0.5 H

# Cell
class DCMotor():
    """DCMotor implements a direct current motor."""
    def __init__(self, x0, params):
        self._params  = params

        self._x0 = x0
        self._x = x0
        self._J_load = 0
        self._update_motor_matrix()

        self._load = False

    def _update_motor_matrix(self):
        # state variables are: position (theta), rotation speed (w, or theta_dot) and current (i)
        self._A = np.array([
            [0, 1, 0],
            [0, -self._params.b/(self._params.J+self._J_load),  self._params.K/(self._params.J+self._J_load)],
            [0, -self._params.K/self._params.L,  -self._params.R/self._params.L]
            ])
        self._B = np.array([[0],[0],[1/self._params.L]])
        self._C = np.array([
            [1, 0, 0], # position
            [0, 1, 0]  # velocity
        ])
        self._D = 0;

    def step(self, dt, u):
        """Runs one step of the motor model, and outputs the resulting torque."""
        self._x = self._x + dt*(self._A@self._x + self._B*u)
        self._x[0] = wrap(self._x[0]) # wrap theta to stay between -pi and pi
        torque = self._params.K*self._x[1,0] # motor torque
        return torque

    def reset(self):
        self._x = self._x0

    def set_load_parameters(self, J_load):
        self._params.J += J_load
        self.update_motor_matrix()

    def connect_to(self, load):
        self._load = load
        self._params.J = load.moment_of_inertia()
        self._update_motor_matrix()

    def _output_equation(self):
        return self._C@self._x

    def measure(self):
        # We need to move this function out of the DCMotor class.
        return np.array([[self._load.position()], [self._load.speed()]]) \
                        if self._load else self._output_equation()



    def get_motor_torque(self):
        """the motor torque is proportional to only the armature current `i` by a constant factor `K`: T=K*i"""
        return self._params.K*self._x[1,0]

# Cell
class PID():
    """PID controller."""
    def __init__(self, Kp, Kd, Ki):
        self.Kp = Kp
        self.Kd = Kd
        self.Ki = Ki
        self._error_old = 0
        self._error_I  = 0

    def control(self, dt, y_des, y):
        """Controls position to a desired (y_des) value.
        Inputs:
          - dt: seconds (sampling time)
          - y_des: m (desired value)
          - y: m (measured value)
        """
        # apply controller
        error = y_des - y
        error_dot = (error - self._error_old)/dt
        self._error_I   += error*dt
        self._error_old = error
        # controller
        return self.Kp*error + self.Kd*error_dot + self.Ki*self._error_I


# Cell
class Simulator():
    def __init__(self, pendulum, motor, controller):
        self._pendulum = pendulum
        self._motor = motor
        self._controller = controller
        self._data = defaultdict(list)

    def y_des(self, y):
        """Set the desired final position of the pendulum in degrees."""
        self.y_des = y

    def run(self, t0, tf, dt):
        time = np.arange(t0, tf, dt)

        for t in time:
            u = self._controller.control(dt, y_des=np.radians(self.y_des),
                                             y=self._pendulum.position())
            torque = self._motor.step(dt, u)
            self._pendulum.step(dt, u=torque)

            self._data['error (m)'].append(np.radians(self.y_des) \
                                           - self._pendulum.position())
            self._data['position (rad)'].append(self._pendulum.position())
            self._data['speed (rad/s)'].append(self._pendulum.speed())
            self._data['torque (N.m)'].append(torque)

        self._data['time (s)'] = time
        return self._data


# Cell
class AnimateControlledPendulum():
    """See also: https://jakevdp.github.io/blog/2012/08/18/matplotlib-animation-tutorial/"""
    def __init__(self, sim):
        self._sim = sim

        self._fig = plt.figure()
        self._ax = self._fig.add_subplot(111, aspect='equal', autoscale_on=False,
                                 xlim=(-.5, .5), ylim=(-.5, 0))
        self._ax.grid()
        self._line, = self._ax.plot([], [], 'o-', lw=2)

        self._title = self._ax.text(0.5, 1.05, "", #bbox={'facecolor':'w', 'alpha':0.5, 'pad':5},
                    transform=self._ax.transAxes, ha="center")

    def animate_init(self):
        """Initialize animation.
           Plot the background of each frame. """
        self._line.set_data([], [])
        return self._line

    def animate(self, i):
        """Animation function.
           This is called sequentially to perform animation step"""
        rod_end_1, rod_end_2 = self._sim._pendulum.rod_position_at(np.degrees(self._sim._data['position (rad)'][i]))
        self._line.set_data([rod_end_1[0], rod_end_2[0]], [rod_end_1[1], rod_end_2[1]])
        self._title.set_text(u"t = {:.1f}s".format(self._sim._data['time (s)'][i]))
        return self._line, self._title

    def start_animation(self, t0, tf, dt):
        # choose the interval based on dt and the time to animate one step
        t_start = time.time()
        self.animate(0)
        t_end = time.time()
        interval = 1000 * dt - (t_end - t_start)
        n_frames = int((tf-t0)/dt)

        # call the animator. blit=True means only re-draw the parts that have changed.
        anim = animation.FuncAnimation(self._fig,
                                       self.animate,
                                       init_func=self.animate_init,
                                       frames=n_frames,
                                       interval=interval,
                                       blit=True,
                                       repeat_delay=10000,
                                       repeat=True);
        plt.close()
        return anim