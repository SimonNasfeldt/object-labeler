# object-labeler
Object labeler with assisted labeling using yolov5 object detection

Requires https://github.com/ultralytics/yolov5 to predict labels, useful to extend dataset from a trained model.\
It has some basic functions for relabeling, example video: https://youtu.be/GN2_ZmBkpUQ

**options.json**
|     Option      |               Description              |
| --------------- | -------------------------------------- |
|   images_path   | Path to the image folder               |
|   labels_path   | Path to the label folder               |
| yolo_directory  | YoloV5 detect.py file                  |
| yolo_weightfile | YoloV5 weight .pt file                 |
|   yolo_output   | Folder where detected labels are saved |
|   class_names   | List of class names                    |

**Controls**
* Right click - remove label
* Left click - create label
* Right arrow key - next image
* Left arrow key - previous image
