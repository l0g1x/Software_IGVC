#!/usr/bin/env python
import sys
import numpy as np
import cv2
import rospy
# from dynamic_reconfigure.server import Server
from lane_detection import LaneDetection
# from line_detection.cfg import LineDetectionConfig
from sensor_msgs.msg import PointCloud
import sensor_msgs
from sensor_msgs.msg import CompressedImage
from geometry_msgs.msg import Point
import rospkg
from itertools import izip
import std_msgs.msg


###############################################################################
# Chicago Engineering Design Team
# Line PointCloud publisher node
#
# Publishes a pointcloud of every non-zero pixel in the input image. The
# pixel_to_coordinate_calculator node must be run at least once before with
# consistent roi settings.
#
# @author Basheer Subei
# @email basheersubei@gmail.com


class PointcloudPublisher(LaneDetection):

    def __init__(self, namespace, node_name):
#        LaneDetection.__init__(self, namespace, node_name)

        # removes trailing slash in namespace
        if (namespace.endswith("/")):
            namespace = namespace[:-1]

        # grab parameters from launch file
        self.subscriber_image_topic = "/threshold/line_image/compressed" 
       
        self.publisher_image_topic = rospy.get_param(
            namespace + node_name + "/publisher_image_topic",
            "/line_image/compressed"
        )
        self.buffer_size = rospy.get_param(
            namespace + node_name + "/buffer_size",
            52428800
        )
        self.package_path = rospkg.RosPack().get_path('line_detection')

        # top-left x coordinate of ROI rectangle
        self.roi_top_left_x = rospy.get_param(
            namespace + node_name + '/roi_x',
            0
        )
        # top-left y coordinate of ROI rectangle
        self.roi_top_left_y = rospy.get_param(
            namespace + node_name + '/roi_y',
            # self.camera_info.height / 2
            0
        )
        # assert(self.roi_x >= 0)
        # assert(self.roi_x < self.camera_info.width)
        # assert(self.roi_y >= 0)
        # assert(self.roi_y < self.camera_info.height)

        # width of ROI rectangle
        self.roi_width = rospy.get_param(
            namespace + node_name + '/roi_width',
            960
        )
        # height of ROI rectangle
        self.roi_height = rospy.get_param(
            namespace + node_name + '/roi_height',
            480
        )

        # initialize ROS stuff

        # set publisher and subscriber

        # publisher for image of line pixels (only for debugging, not used in
        # map)
        self.line_image_pub = rospy.Publisher(
            namespace + "/" + node_name + self.publisher_image_topic,
            sensor_msgs.msg.CompressedImage,
            queue_size=1
        )

        # subscriber for ROS image topic
        self.image_sub = rospy.Subscriber(
            self.subscriber_image_topic,
            CompressedImage,
            self.image_callback,
            queue_size=1,
            buff_size=self.buffer_size
        )

        # remove this publisher that was inherited from LaneDetection
        self.line_image_pub.unregister()

        self.publisher_cloud_topic = rospy.get_param(
            namespace + node_name + "/publisher_cloud_topic",
            "/line_pointcloud"
        )
        # removes trailing slash in namespace
        if (namespace.endswith("/")):
            namespace = namespace[:-1]
        # publisher for line pointcloud
        self.line_cloud_pub = rospy.Publisher(
            namespace + "/" + node_name + self.publisher_cloud_topic,
            PointCloud,
            queue_size=10
        )

    # this is what gets called when an image is received
    def image_callback(self, ros_image):

        cv2_image = LaneDetection.ros_to_cv2_image(self, ros_image)
        # print cv2_image.shape
        roi = LaneDetection.get_roi(self, cv2_image)

        non_zeros = roi.nonzero()
        self.number_of_points = len(non_zeros[0])
        self.line_pointcloud = PointCloud()
        self.line_pointcloud.header = std_msgs.msg.Header()
        self.line_pointcloud.header.stamp = rospy.Time.now()
        self.line_pointcloud.header.frame_id = "base_footprint"
        # create an empty list of correct size
        self.line_pointcloud.points = [None] * self.number_of_points
        count = 0
        for (row, column) in izip(non_zeros[0], non_zeros[1]):
            # print "row: " + str(row) + ", column: " + str(column)
            # print("intersection with ground: " + str(self.intersection_array[column][row]) + ")")
            point = self.intersection_array[row][column]
            self.line_pointcloud.points[count] = Point(point[0], point[1], 0)
            count += 1
        # publishes pointcloud message
        self.line_cloud_pub.publish(self.line_pointcloud)
    # end image_callback()


def main(args):
    node_name = "pointcloud_publisher"
    namespace = rospy.get_namespace()

    # create a BlobDetection object
    pp = PointcloudPublisher(namespace, node_name)

    # start the line_detector node and start listening
    rospy.init_node("pointcloud_publisher", anonymous=True)

    pp.intersection_array = np.load(
        pp.package_path + "/misc/training_images/pixel_coordinates.npy"
    )
    # starts dynamic_reconfigure server
    # srv = Server(LineDetectionConfig, c.reconfigure_callback)
    rospy.spin()

if __name__ == '__main__':
    main(sys.argv)
