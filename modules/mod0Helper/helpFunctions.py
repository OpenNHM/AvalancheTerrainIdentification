"""General helper functions"""


def zDelta2velocity(zDelta):
    """compute velocity from energy line height

    Parameters
    -----------
    zDelta: numpy float or array
        energy line height

    Returns
    -----------
    velocity: numpy float or array
        velocity comuted frm zDelta
    """
    velocity = (zDelta * 2 * 9.81) ** 0.5
    return velocity


def velocity2pressure(velocity, rho):
    """compute pressure from velocity

    Parameters
    --------------
    velocity: numpy float or array
        velocity values
    rho: float
        density of snow

    Returns
    ----------------
    imppressure: numpy float or array
        computed pressure
    """
    pressure = rho * velocity**2 * 1e-3
    return pressure
