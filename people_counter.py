import argparse
import cv2
import os
import time
import imutils
import numpy as np

ENTERED_STRING = "ENTERED_THE_AREA"
LEFT_AREA_STRING = "LEFT_THE_AREA"
NO_CHANGE_STRING = "STAY_IN_AREA"
LOWEST_CLOSEST_DISTANCE_THRESHOLD = 100
SZ_LIMIT1 = 120
SZ_LIMIT2 = 250
line_point1 = (50, 300)
line_point2 = (640 - 50, 300)
top_cascade = cv2.CascadeClassifier('HAAR_3.xml')
_DEBUG_ = False
_OUTPUT_ = False


class Person:
    positions = []
    isCounted = False
    disappear_count = 0

    def __init__(self, position):
        self.positions = [position]

    def update_position(self, new_position):
        self.positions.append(new_position)
        if len(self.positions) > 100:
            self.positions.pop(0)

    def on_opposite_sides(self, y_coord):
        val1 = (self.positions[-2][1] > y_coord) and (self.positions[-1][1] <= y_coord)
        val2 = (self.positions[-2][1] <= y_coord) and (self.positions[-1][1] > y_coord)
        return val1 or val2

    def did_cross_line(self, y_coord):
        if self.on_opposite_sides(y_coord):
            # if abs(self.positions[-1][1] - line_point1[1]) > 50:
            #     return NO_CHANGE_STRING
            if self.positions[-1][1] < line_point1[1]:
                if not self.isCounted:
                    # self.isCounted = True
                    return ENTERED_STRING
                else:
                    self.disappear_count += 1
                    return NO_CHANGE_STRING
            else:
                if not self.isCounted:
                    # self.isCounted = True
                    return LEFT_AREA_STRING
                else:
                    self.disappear_count += 1
                    return NO_CHANGE_STRING
        else:
            self.disappear_count += 1
            return NO_CHANGE_STRING

    def distance_from_last_x_positions(self, new_position, x):
        (x1, y1) = self.positions[-1]
        (x2, y2) = new_position
        return int(np.sqrt((x1 - x2) ** 2 + (y1 - y2) ** 2))
        '''
        total = [0, 0]
        z = x
        while z > 0:
            if len(self.positions) > z:
                total[0] += self.positions[-(z + 1)][0]
                total[1] += self.positions[-(z + 1)][1]
            else:
                x -= 1
            z -= 1
        if total[0] < 1 or total[1] < 1:
            return abs(self.positions[0][0] - new_position[0]) + abs(self.positions[0][1] - new_position[1])
        total[0] = total[0] / x
        total[1] = total[1] / x

        return abs(new_position[0] - total[0]) + abs(new_position[1] - total[1])
        '''


def get_video():
    ap = argparse.ArgumentParser()
    ap.add_argument("-v", "--video", default="video/zenital2.avi", help="path to the video file")
    args = vars(ap.parse_args())

    # get video from webcam
    if args.get("video", None) is None:
        camera = cv2.VideoCapture(0)
        time.sleep(0.25)
        return camera
    # get video from file
    else:
        camera = cv2.VideoCapture(0)
        time.sleep(0.25)
        return camera


def testNeighbourIn(x, y, x0, y0, d):
    dis = (x - x0) ** 2 + (y - y0) ** 2
    if dis < d ** 2:
        return True
    return False


def checkFixed(prvs, curs):
    result = []
    if len(prvs) == 0:
        return result
    for box in curs:
        [cx, cy, _] = box
        is_again = False
        for new_box in prvs:
            [cx1, cy1, _] = new_box
            if testNeighbourIn(cx, cy, cx1, cy1, 20) or not testNeighbourIn(cx, cy, cx1, cy1, 40):
                is_again = True
                break
        if not is_again:
            result.append(box)
    return result


def main():
    outVideo = 'video/out.avi'
    if os.path.exists(outVideo):
        os.remove(outVideo)

    camera = get_video()

    people_list = []
    inside_count = 0
    outside_count = 0
    frame_width = 640
    frame_height = 480
    prev_frame = 0

    ret, img = camera.read()
    if not ret:
        print("Can't read video file!")
        exit(1)
    else:
        frame_height = len(img)
        frame_width = len(img[0])
    first_cap = True
    if _OUTPUT_:
        out = cv2.VideoWriter(outVideo, cv2.VideoWriter_fourcc('M', 'J', 'P', 'G'), 10, (frame_width, frame_height))
    msg = ""
    nFrames = 0

    while True:
        ret, img = camera.read()
        if not ret:
            break
        nFrames += 1
        if nFrames < 250:
            prev_frame = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            continue

        img = imutils.resize(img, width=640)
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        peoples = top_cascade.detectMultiScale(gray, 1.1, 5, cv2.CASCADE_SCALE_IMAGE, \
                                               (SZ_LIMIT1, SZ_LIMIT1), (SZ_LIMIT2, SZ_LIMIT2))

        # draw cross - line
        cv2.line(img, line_point1, line_point2, (255, 0, 255), 2, 1)

        for (x, y, w, h) in peoples:

            try:
                frameDelta = cv2.absdiff(prev_frame[x:x + w - 1, y:y + h - 1], gray[x:x + w - 1, y:y + h - 1])
                thresh1 = np.mean(frameDelta)
            except (RuntimeError, TypeError, NameError):
                continue
            if thresh1 < 15:
                continue

            # calculate center point
            [cx, cy] = [x + w // 2, y + h // 2]

            if cy < line_point1[1]-100:
                continue
            # draw detected rect
            cv2.rectangle(img, (x, y), (x + w, y + h), (255, 0, 0), 1)
            cv2.circle(img, (cx, cy), 2, (0, 0, 255), 3)

            lowest_closest_distance = float("inf")
            closest_person_index = None
            rectangle_center = (cx, cy)

            for i in range(0, len(people_list)):
                dist = people_list[i].distance_from_last_x_positions(rectangle_center, 3)
                if lowest_closest_distance > dist:
                    lowest_closest_distance = dist
                    closest_person_index = i
            if lowest_closest_distance > 100:
                closest_person_index = None
            if closest_person_index is not None:
                if lowest_closest_distance < LOWEST_CLOSEST_DISTANCE_THRESHOLD:
                    people_list[i].update_position(rectangle_center)
                    change = people_list[i].did_cross_line(line_point1[1])
                    if change == ENTERED_STRING:
                        inside_count += 1
                    elif change == LEFT_AREA_STRING:
                        # outside_count += 1
                        pass
                else:
                    new_person = Person(rectangle_center)
                    people_list.append(new_person)
            else:
                if rectangle_center[1] < line_point1[1]:
                    continue
                new_person = Person(rectangle_center)
                people_list.append(new_person)
        # draw history
        if _DEBUG_:
            for i in range(0, len(people_list)):
                pe = people_list[i]
                for pos in range(0, len(pe.positions)):
                    cv2.circle(img, pe.positions[pos], 1, (255, 255, 0), 2)

        for candi in people_list:
            if candi.isCounted:
                # people_list.remove(candi)
                pass

        if first_cap:
            first_cap = False

        msg = "In: {0}, Out1: {1}".format(inside_count, outside_count)
        cv2.putText(img, msg, (10, 50), cv2.FONT_HERSHEY_PLAIN, 2, (0, 255, 255))

        cv2.imshow('result', img)
        if _OUTPUT_:
            out.write(img)

        prev_frame = gray

        if _DEBUG_:
            print("To continue, press key(c)")
            finish = False
            while True:
                k = cv2.waitKey(0) & 0xff
                if k == ord('c'):
                    break
                elif k == 27:
                    finish = True
                    break
                continue
            if finish:
                break
        else:
            k = cv2.waitKey(33) & 0xff
            if k == 27:
                break

    camera.release()
    if _OUTPUT_:
        out.release()
    cv2.destroyAllWindows()

    print(msg)


if __name__ == '__main__':
    main()
    print("Finished detection!")
