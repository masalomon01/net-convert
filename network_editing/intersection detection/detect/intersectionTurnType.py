'''
Created on Nov 16, 2015

@author: asifrehan
'''
import math
def intersectionTurnType(linkA_orien, linkB_orien):
    """
    turnType = 1 if right turn
    turnType = 2 if left turn
    turnType = 3 if u-turn
    turnType = 4 if thru turn
    """
    angle_dif_rad = linkB_orien - linkA_orien
    thru_uturn_tol = 40
    left_right_tol = 50

    if round(math.sin(math.radians(90-left_right_tol)), 2) <=   \
                            round(math.sin(math.radians(angle_dif_rad)),2):
        turnType = 1
    if round(math.sin(math.radians(-90-left_right_tol)),2) >=  \
                            round(math.sin(math.radians(angle_dif_rad)),2) :
        turnType = 2
    #sharp turn on left and right both considered as u-turn
    #can be improved by considering such positive angle_dif_rad values
    if abs(abs(angle_dif_rad)-180) < thru_uturn_tol:
        turnType = 3 
    elif round(math.sin(math.radians(-thru_uturn_tol)),2) <  \
                        round(math.sin(math.radians(angle_dif_rad)),2) <  \
                        round(math.sin(math.radians(thru_uturn_tol)),2):
        turnType = 4
    return turnType
if __name__ == '__main__':
    pass