import os
import time
import threading
from queue import Queue
import win32gui
from win32api import GetSystemMetrics
import mss
import mss.tools
from pynput.keyboard import Key, Listener

class InputCapture:
    def __init__(self, gameWindowName, dt, sessionsFolder):
        self.dt = dt

        if not os.path.isdir(sessionsFolder):
            print("Error: Sessions directory {} is not a valid directory. Aborting.".format(sessionsFolder))
            exit()
        try:
            sessNums = [int(folderName) for folderName in os.listdir(sessionsFolder)]
            self.sessFolder = "{}/{}/".format(sessionsFolder, max(sessNums)+1)
        except:
            self.sessFolder = "{}/1/".format(sessionsFolder)

        os.mkdir(self.sessFolder)
        self.capsFolder = self.sessFolder + "caps/"
        os.mkdir(self.capsFolder)

        self.gameBbox = self.getWindowBbox(gameWindowName)
        self.capNumber = 0
        self.isCapturing = True
        self.sct = mss.mss()

        self.keys = [Key.up, Key.right, Key.down, Key.left]
        self.keyStates = {key : False for key in self.keys}
        self.inputQueue = Queue()

        self.labelFile = open(self.sessFolder + "labels.txt", mode="a")

        self.captureThread = threading.Thread(target=self.captureFrames)
        self.captureThread.start()

        with Listener(on_press=self.onKeyPress,on_release=self.onKeyRelease) as listener:
            listener.join()
            print("Listener thread joined.")
        
        self.labelFile.close()

    def getWindowBbox(self, windowName):
        gameWindow = win32gui.FindWindow(None, windowName)
        if gameWindow == 0:
            print("Could not find game window for \"" + windowName + "\". Exiting.")
            exit()
        win32gui.SetForegroundWindow(gameWindow)


        print('Width: ', GetSystemMetrics(0))
        print('Height: ', GetSystemMetrics(1))
        bbox = list(win32gui.GetWindowRect(gameWindow))
        bbox[0] += 8
        bbox[1] += 31
        width = bbox[2]-bbox[0]
        height = bbox[3]-bbox[1]
        return {'top': bbox[1], 'left': bbox[0], 'width': width-8, 'height': height-8}
        
    def captureFrames(self):
        # TODO: see if using windows api calls is faster https://www.quora.com/How-can-we-take-screenshots-using-Python-in-Windows
        while self.isCapturing:
            tic = time.time()
            while not self.inputQueue.empty():
                currInput, isPress = self.inputQueue.get()
                self.keyStates[currInput] = isPress
            
            label = 0
            for keyIndex, key in enumerate(self.keys):
                if self.keyStates[key]:
                    if label != 0:
                        print("Warning: multiple inputs encountered, discarding everything but {}.".format(keyIndex))
                    label = keyIndex+1 # none is 0, but self.keys starts at 0, so we add 1 to all
            self.labelFile.write(str(label)+'\n')

            # Grab the data
            sct_img = self.sct.grab(self.gameBbox)
            # Save to the picture file
            fileName = self.capsFolder + str(self.capNumber) + ".png"
            mss.tools.to_png(sct_img.rgb, sct_img.size, output=fileName)

            self.capNumber += 1

            sleepAmount = self.dt-(time.time()-tic)
            if sleepAmount < 0:
                print('Lagging, missed frame by {}'.format(-sleepAmount))
                sleepAmount = 0
            time.sleep(sleepAmount)

    def onKeyPress(self, key):
        if key in self.keys: # discard input not in the list of expected keys
            self.inputQueue.put((key, True))
        elif key == Key.esc:
            # stop the game capture thread
            self.isCapturing = False
            print('Waiting for thread...')
            self.captureThread.join()
            print('Thread joined, exiting.')
            # stop the keyboard listener thread
            return False
    
    def onKeyRelease(self, key):
        if key in self.keys: # discard input not in the list of expected keys
            self.inputQueue.put((key, False))

if __name__ == '__main__':
    g1 = "Crypt of the NecroDancer"

    inputCapture = InputCapture(g1, 1/14.0, "sessions")