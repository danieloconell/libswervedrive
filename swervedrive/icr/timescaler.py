import numpy as np
import math
from typing import List


class TimeScaler:
    def __init__(self, beta_dot_bounds: List, beta_2dot_bounds: List,
                 phi_2dot_bounds: List):
        """
        Initialize the TimeScaler object.
        :param dbeta_bounds: Min/max allowable value for rotation rate of
        modules, in rad/s
        :param d2beta_bounds: Min/max allowable value for the angular
        acceleration of the modules, in rad/s^2.
        :param d2phi_bounds: Min/max allowable value for the angular
        acceleration of the module wheels, in rad/s^2.
        """
        self.beta_dot_b = beta_dot_bounds
        self.beta_2dot_b = beta_2dot_bounds
        self.phi_2dot_b = phi_2dot_bounds

    def compute_scaling_bounds(self, dbeta: np.ndarray, d2beta: np.ndarray,
                               dphi_dot: np.ndarray):
        """
        Compute bounds of the scaling factors for the motion.
        This function effectively computes bounds such that the possibly
        arbitrarily high amplitude of the commands from the kinematic model
        obeys the physical constraints of the robot motion.
        :param dbeta: command for derivative of the angle of the modules.
        :param d2beta: command for second derivative of the angle of the modules.
        :param dphi_dot: command for derivative of angular velocity of the
        module wheels.
        :returns: upper and lower scaling bounds for derivative of s and second
        derivative of s: ds_lower, ds_upper, d2s_lower, d2s_upper.
        """
        if (in_range(dbeta, self.beta_dot_b)
                and in_range(d2beta, self.beta_2dot_b)
                and in_range(dphi_dot, self.phi_2dot_b)):
            # all of the differential constraints are already satisfied, so
            # no scaling is required
            return 0, 1, 0, 1

        # we ignore the corresponding constraints if their governing command
        # value is close to zero
        # TODO: figure out what the tolerances should be
        ignore_beta = math.isclose(dbeta, 0, abs_tol=1e-2)
        ignore_phi = math.isclose(dphi_dot, 0, abs_tol=1e-2)

        ds_lower, ds_upper, d2s_lower, d2s_upper = 0, 1, 0, 1

        if not ignore_beta:
            # need to reverse inequality if we have a negative
            (lower, upper) = (1, 0) if dbeta < 0 else (0, 1)
            # equation 36a in control paper
            ds_lower = max(ds_lower,
                           self.beta_2dot_b[lower]/dbeta)
            ds_upper = min(ds_upper,
                           self.beta_2dot_b[upper]/dbeta)
        if not ignore_phi:
            (lower, upper) = (1, 0) if dphi_dot < 0 else (0, 1)
            # equation 36c in control paper
            ds_lower = max(ds_lower,
                           self.phi_2dot_b[lower]/dphi_dot)
            ds_upper = min(ds_upper,
                           self.phi_2dot_b[upper]/dphi_dot)

        if not ignore_beta:
            # apply constraint on second derivative
            # must calculate here as it depends on the value of s_dot, which
            # in turn is defined by the value of ds_upper
            s_dot = ds_upper # we pick the maximum value for s_dot
            (lower, upper) = (1, 0) if dbeta < 0 else (0, 1)
            d2s_lower = max(d2s_lower,
                            (self.beta_2dot_b[lower]-d2beta*(s_dot**2))
                            / dbeta)
            d2s_upper = min(d2s_upper,
                            (self.beta_2dot_b[upper]-d2beta*(s_dot**2))
                            / dbeta)

        return ds_lower, ds_upper, d2s_lower, d2s_upper

    def compute_scaling_parameters(self, ds_lower: float, ds_upper: float,
                                   d2s_lower: float, d2s_upper: float):
        """
        Compute the scaling parameters used to scale the motion. This function
        assumes that for both ds and d2s lower <= upper (ie the interval is
        not empty.) Sets the scaling parameters as object variables read when
        scale_motion is called.
        :param ds_lower: derivative of parameter s, lower bound.
        :param ds_upper: derivative of parameter s, upper bound.
        :param d2s_lower: second derivative of parameter s, lower bound.
        :param d2s_upper: second derivative of parameter s, upper bound.
        """
        self.s_dot = ds_upper
        self.s_2dot = d2s_upper

    def scale_motion(self, dbeta: np.ndarray, d2beta: np.ndarray,
                     dphi_dot: np.ndarray):
        """
        Scale the actuators' motion using the scaling bounds.
        :param dbeta: command for derivative of the angle of the modules.
        :param d2beta: command for second derivative of the angle of the modules.
        :param dphi_dot: command for derivative of angular velocity of the
        module wheels.
        :returns: *time* derivatives of actuators motion beta_dot, beta_2dot, phi_2dot
        """

        beta_dot = dbeta * self.s_dot
        beta_2dot = d2beta*(self.s_dot**2) + dbeta * self.s_2dot
        phi_2dot = dphi_dot * self.s_dot

        return beta_dot, beta_2dot, phi_2dot


def in_range(value, rng):
    """ Check if value is in the range of list[0], list[1] """
    return rng[0] <= value <= rng[1]
