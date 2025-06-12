from PyQt6.QtWidgets import (
    QApplication,
    QMainWindow,
    QPushButton,
    QHBoxLayout,
    QVBoxLayout,
    QWidget,
    QTextEdit,
    QLineEdit,
)
from matplotlib.figure import Figure
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from PyQt6.QtWidgets import QMessageBox
from PyQt6 import QtCore
import numpy as np
from PyQt6.QtWidgets import QSlider, QLabel
from PyQt6.QtCore import Qt
import deapi
import time
import os
import shutil
from scipy.ndimage import generic_filter
from skimage.morphology import dilation, disk


def var_2d(arr, factor):
    new_shape = (arr.shape[0] // factor, factor, arr.shape[1] // factor, factor)
    return np.var(arr.reshape(new_shape), axis=(1, 3))


def rebin_2d(arr, factor):
    new_shape = (arr.shape[0] // factor, factor, arr.shape[1] // factor, factor)
    return np.mean(arr.reshape(new_shape), axis=(1, 3))


def mask2bad_pixel_file(mask, raw, output_file: str):
    file_str = '<?xml version="1.0" encoding="utf-8"?>\n\n<BadPixels>\n\n    <BadPixelMap CentroidMode="2">\n\n'
    file_str += f"<!--Super-resolution & CES modes   Image Size: {mask.shape} -->\n"
    positions = np.argwhere(mask)
    for p in positions:
        file_str += f'        <Defect Column="{p[1]}" Row="{p[0]}" /> <!-- Value: {raw[p[0], p[1]]} -->\n'

    file_str += "    </BadPixelMap>\n"
    file_str += "</BadPixels>"

    parent_directory = os.path.abspath(os.path.join(output_file, os.pardir))
    archive_dir = parent_directory + "\\Archive"
    # Create a directory along with any necessary intermediate directories
    if not os.path.exists(archive_dir):
        os.makedirs(archive_dir)
    loc_time = time.localtime()
    shutil.copy2(
        output_file,
        archive_dir
        + f"\\{loc_time.tm_year}-{loc_time.tm_mon}-{loc_time.tm_mday}-{loc_time.tm_hour}-{loc_time.tm_min}-{loc_time.tm_sec}.xml",
    )
    with open(output_file, "w+") as f:
        f.write(file_str)


class BadPixelCorrectionWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Bad Pixel Correction")
        self.resize(1300, 500)

        # Create the big plot
        self.big_plot_canvas = FigureCanvas(Figure(figsize=(5, 5)))
        self.big_plot_axes = self.big_plot_canvas.figure.add_subplot(111)
        self.big_plot_axes.set_title("Big Plot")

        self.big_plot_image = self.big_plot_axes.imshow(
            np.random.rand(512, 512), interpolation="none"
        )

        # Create smaller plots
        self.small_plot_axes = []
        self.small_plot_canvases = FigureCanvas(Figure(figsize=(5, 7)))
        self.small_plot_images = []
        for i in range(9):
            self.small_plot_axes.append(
                self.small_plot_canvases.figure.add_subplot(3, 3, i + 1)
            )
            self.small_plot_images.append(
                self.small_plot_axes[i].imshow(np.ones((10, 10)))
            )
            self.small_plot_axes[i].set_yticks([])
            self.small_plot_axes[i].set_xticks([])
        self.small_plot_axes[0].set_title("Uncorrected")
        self.small_plot_axes[1].set_title("Mask")
        self.small_plot_axes[2].set_title("Corrected")

        # Create text output panel
        self.text_output = QTextEdit()
        self.text_output.setReadOnly(True)
        self.text_output.setPlaceholderText("Output messages will appear here...")

        # Create range slider
        self.range_slider_min = QSlider(Qt.Orientation.Vertical)
        self.range_slider_min.setMinimum(0)
        self.range_slider_min.setMaximum(100)
        self.range_slider_min.setValue(20)
        self.range_slider_min.valueChanged.connect(self.update_range_labels)

        self.range_slider_max = QSlider(Qt.Orientation.Vertical)
        self.range_slider_max.setMinimum(0)
        self.range_slider_max.setMaximum(100)
        self.range_slider_max.setValue(80)
        self.range_slider_max.valueChanged.connect(self.update_range_labels)

        self.range_label_min = QLabel("Min: 20")
        self.range_label_max = QLabel("Max: 80")
        self.range_label_max.setMinimumWidth(50)
        self.range_label_min.setMinimumWidth(50)

        self.timer = QtCore.QTimer()
        self.timer.setInterval(10)  # Every 10ms we will check to update the plots??
        self.timer.timeout.connect(self.update_plots)
        self.timer.start()

        # Set layout
        main_layout = QVBoxLayout()
        all_plots_layout = QHBoxLayout()
        all_plots_layout.addWidget(self.text_output)
        plots_layout = QHBoxLayout()
        # Add big plot
        plots_layout.addWidget(self.big_plot_canvas)
        plots_layout.addWidget(self.small_plot_canvases)

        # Add smaller plots
        all_plots_layout.addLayout(plots_layout)

        # Add range slider to layout
        slider_layout = QHBoxLayout()
        slider_layout_vbox = QVBoxLayout()
        slider_layout_vbox.addWidget(self.range_slider_min)
        slider_layout_vbox.addWidget(self.range_label_min)
        slider_layout.addLayout(slider_layout_vbox)
        slider_layout_vbox2 = QVBoxLayout()
        slider_layout_vbox2.addWidget(self.range_slider_max)
        slider_layout_vbox2.addWidget(self.range_label_max)
        slider_layout.addLayout(slider_layout_vbox2)
        all_plots_layout.addLayout(slider_layout)

        main_layout.addLayout(all_plots_layout)

        # Set central widget
        container = QWidget()

        button_layout = QHBoxLayout()
        self.start_button = QPushButton("Get Raw")
        self.start_button.clicked.connect(self.toggle_start_stop_bad_pixel)
        self.start_button.setCheckable(True)
        button_layout.addWidget(self.start_button)

        self.is_acquiring_raw = False
        self.is_acquiring_corrected = False
        self.roi_button = QPushButton("New ROI")
        self.roi_button.clicked.connect(self.push_roi_button)
        button_layout.addWidget(self.roi_button)

        self.dilation_button = QPushButton("Dilate Min")
        self.dilation_button.clicked.connect(self.toggle_dilate)
        self.dilation_button.setCheckable(True)
        self.dilation_button.setChecked(False)

        self.dilation_button_max = QPushButton("Dilate max")
        self.dilation_button_max.clicked.connect(self.toggle_dilate)
        self.dilation_button_max.setCheckable(True)
        self.dilation_button_max.setChecked(False)

        button_layout.addWidget(self.dilation_button)
        button_layout.addWidget(self.dilation_button_max)
        self.test_bad_pixel = QPushButton("Test Bad Pixel Mask")
        self.test_bad_pixel.clicked.connect(self.test_bad_pixel_func)
        button_layout.addWidget(self.test_bad_pixel)

        self.save_correction = QPushButton("Save Bad Pixel Correction")
        self.save_correction.clicked.connect(self.save_correction_func)
        button_layout.addWidget(self.save_correction)

        # Add acquisition time input
        label = QLabel("Acq. Time (seconds):")
        self.acquisition_time_input = QLineEdit()
        self.acquisition_time_input.setFixedWidth(40)
        self.acquisition_time_input.setText(str(self.acquisition_time))
        self.acquisition_time_input.editingFinished.connect(
            self.update_acquisition_time
        )

        # Add the input to the layout
        button_layout.addWidget(label)
        button_layout.addWidget(self.acquisition_time_input)
        main_layout.addLayout(button_layout)

        # Add the start/stop button to the layout
        container.setLayout(main_layout)

        self.setCentralWidget(container)
        self.show()

        self.client = deapi.Client()
        self.client.connect()
        self.text_output.append(f"Connected to Client:{self.client}")

        self.raw_image = None
        self.corrected_image = None
        self.sub_images = []
        self.sub_images_masks = []

        self.current_indexes = [0, 1, 2]
        self.num_rois = 15
        self.max_threshold = 1000

        self.acquisition_time = 120
        loc_time = time.localtime()
        self.slices = []

        self.directory_out = f"D:\\Service\\BadPixels\\{loc_time.tm_year}-{loc_time.tm_mon}-{loc_time.tm_mday}"

    def update_acquisition_time(self):
        try:
            self.acquisition_time = int(self.acquisition_time_input.text())
            self.text_output.append(
                f"Acquisition time updated to: {self.acquisition_time} seconds"
            )
        except ValueError:
            self.text_output.append(
                "Invalid acquisition time entered. Please enter a valid integer."
            )

    @property
    def dilate_min(self):
        return self.dilation_button.isChecked()

    @property
    def dilate_max(self):
        return self.dilation_button_max.isChecked()

    def update_masks(self):
        if len(self.sub_images) > 0:
            max_value = self.range_slider_max.value()
            min_value = self.range_slider_min.value()
            self.sub_images_masks = []

            for image in self.sub_images:
                min = image < min_value
                max = image > max_value
                if self.dilate_min:
                    min = dilation(min, disk(2))
                if self.dilate_max:
                    max = dilation(max, disk(2))

                mask = np.logical_or(min, max)
                self.sub_images_masks.append(mask)

            for ind, i in zip(
                self.current_indexes,
                [1, 4, 7],
            ):
                self.small_plot_images[i].set_data(self.sub_images_masks[ind])
                # self.small_plot_images[i].set_data(np.random.rand(10,10))
                self.small_plot_images[i].set_clim(0, 1)

            self.small_plot_canvases.draw()
            self.small_plot_canvases.flush_events()

    def update_uncorrected_images(self):
        if len(self.sub_images) > 0:
            for i, ind in zip([0, 3, 6], self.current_indexes):
                # self.small_plot_images[i].set_data(np.random.rand(10,10))
                self.small_plot_images[i].set_data(self.sub_images[ind])
                self.small_plot_images[i].set_clim(
                    np.min(self.sub_images[ind]), self.max_threshold
                )
            self.small_plot_canvases.draw_idle()

    def update_corrected_images(self):
        if self.corrected_image is not None:
            for i, ind in zip([2, 5, 8], self.current_indexes):
                sl = self.slices[ind]
                self.small_plot_images[i].set_data(self.corrected_image[sl[0], sl[1]])
                self.small_plot_images[i].set_clim(
                    np.min(self.sub_images[ind]), self.max_threshold
                )
            self.small_plot_canvases.draw_idle()

    def update_plots(self):
        if (
            self.is_acquiring_raw
            and not self.client.acquiring
            and self.client["Autosave Status"] not in ["Starting", "In Progress"]
        ):
            self.text_output.append("Updating Plots")
            frameType = deapi.data_types.FrameType.TOTAL_SUM_INTEGRATED

            image, pix, attr, hist = self.client.get_result(frameType=frameType)

            self.raw_image = image

            self.max_threshold = int(np.mean(image) + 10 * np.std(image))

            self.range_slider_min.setMinimum(np.min(image))
            self.range_slider_min.setMaximum(self.max_threshold)
            self.range_slider_min.setValue(
                int(np.mean(image) - 3 * np.std(image))
            )  # 5 std away from mean

            self.range_slider_max.setMinimum(np.min(image))
            self.range_slider_max.setMaximum(np.max(image))
            self.range_slider_max.setValue(
                int(np.mean(image) + 3 * np.std(image))
            )  # 5 std away from mean

            # self.big_plot_axes.imshow(image[::4,::4])
            binned_image = rebin_2d(image, 4)
            self.big_plot_image.set_data(
                binned_image
            )  # matplotlib is unhappy with 8k x 8k
            self.big_plot_image.set_clim(np.min(binned_image), self.max_threshold)

            self.big_plot_axes.set_yticks([])
            self.big_plot_axes.set_xticks([])

            panels = var_2d(image, 128)
            self.sub_images = []
            var_arg = np.argsort(panels, None)

            print(panels)
            panel_args = np.unravel_index(var_arg, panels.shape)
            self.slices = []
            for i in range(self.num_rois):
                x_slice = slice(
                    panel_args[0][::-1][i] * 128, (panel_args[0][::-1][i] + 1) * 128
                )
                y_slice = slice(
                    panel_args[1][::-1][i] * 128, (panel_args[1][::-1][i] + 1) * 128
                )

                self.slices.append((x_slice, y_slice))
                self.text_output.append(f"{x_slice}, {y_slice}")
                self.sub_images.append(image[x_slice, y_slice])

            self.update_uncorrected_images()

            self.update_masks()

            self.text_output.append(f"{panel_args}")

            self.text_output.append("Plots updated...")
            self.big_plot_canvas.draw_idle()
            if self.start_button.text() == "Stop":
                self.start_button.setText("Get Raw")
            self.is_acquiring_raw = False
        if (
            self.is_acquiring_corrected
            and not self.client.acquiring
            and self.client["Autosave Status"] not in ["Starting", "In Progress"]
        ):
            self.text_output.append("Updating Plots")
            frameType = deapi.data_types.FrameType.TOTAL_SUM_INTEGRATED

            image, pix, attr, hist = self.client.get_result(frameType=frameType)
            self.corrected_image = image
            self.max_threshold = int(np.mean(image) + 10 * np.std(image))
            binned_image = rebin_2d(image, 4)
            self.big_plot_image.set_data(
                binned_image
            )  # matplotlib is unhappy with 8k x 8k
            self.big_plot_image.set_clim(np.min(binned_image), self.max_threshold)

            self.big_plot_axes.set_yticks([])
            self.big_plot_axes.set_xticks([])

            self.update_corrected_images()

            self.text_output.append("Plots updated...")
            self.big_plot_canvas.draw_idle()
            if self.test_bad_pixel.text() == "Stop":
                self.test_bad_pixel.setText("Test Bad Pixel Mask")
            self.is_acquiring_corrected = False

    def update_range_labels(self):
        if self.range_slider_min.value() > self.range_slider_max.value():
            self.range_slider_min.setValue(self.range_slider_max.value())

        self.range_label_min.setText(f"Min: {self.range_slider_min.value()}")
        self.range_label_max.setText(f"Max: {self.range_slider_max.value()}")
        self.update_masks()
        self.small_plot_canvases.draw_idle()

    def push_roi_button(self):
        self.text_output.append("Getting 3 new ROIs")

        self.current_indexes = np.random.randint(0, self.num_rois, 3)
        self.update_uncorrected_images()
        self.update_masks()
        self.update_corrected_images()

    def toggle_dilate(self):
        self.text_output.append(
            f"Setting Dilate(min, max): {self.dilate_min} {self.dilate_max}"
        )

        self.update_uncorrected_images()
        self.update_masks()

    def get_full_mask(self):
        max_value = self.range_slider_max.value()
        min_value = self.range_slider_min.value()

        min = self.raw_image < min_value
        max = self.raw_image > max_value
        if self.dilate_min:
            min = dilation(min, disk(2))
        if self.dilate_max:
            max = dilation(max, disk(2))

        mask = np.logical_or(min, max)

        return mask

    def test_bad_pixel_func(self):
        if self.test_bad_pixel.text() == "Test Bad Pixel Mask":
            if self.start_button.text() == " Stop":
                pass  # Do Nothing
            else:
                self.test_bad_pixel.setText("Stop")
                self.text_output.append("Creating Bad Pixel Mask")

                mask = self.get_full_mask()
                file = self.client["File Path - Bad Pixels"]

                mask2bad_pixel_file(mask, self.raw_image, file)
                # self.client["Image Processing - Bad Pixel Correction"] = "Off"
                self.text_output.append(f"Writing Temperary Bad Pixel file to:{file}")

                bad_pixel_file = self.client["File Path - Bad Pixels"]
                self.client["Image Processing - Bad Pixel Correction"] = "On"
                time.sleep(3)

                self.client["Image Processing - Flatfield Correction"] = "None"

                self.client["Autosave Directory"] = self.directory_out
                self.client["Autosave Final Image"] = "On"
                self.client["Exposure Time (seconds)"] = self.acquisition_time
                # self.client["Frame Count"] = num_frames
                self.client["Autosave Filename Suffix"] = "BadPixelCorrected"
                self.text_output.append(
                    f"Starting Acquiring: For {self.acquisition_time} sec"
                )

                self.client.start_acquisition(1)
                self.is_acquiring_corrected = True

        else:
            self.test_bad_pixel.setText("Get Raw")
            self.text_output.append("Stopping Testing Pixel Correction...")
            self.client.stop_acquisition()
            # Add logic for stopping the process here

    def save_correction_func(self):
        self.text_output.append("Saving Bad Pixel Correction")
        # Add logic for saving the correction here
        mask = self.get_full_mask()
        bad_pixel_dir = self.directory_out + "\\Final"

        file = self.client["File Path - Bad Pixels"]
        mask2bad_pixel_file(mask, self.raw_image, file)

    def toggle_start_stop_bad_pixel(self):
        if self.start_button.text() == "Get Raw":
            if self.test_bad_pixel.text() == "Stop":
                pass  # Do nothing
            else:
                self.start_button.setText("Stop")

                # Show a pop-up message
                msg_box = QMessageBox()
                msg_box.setIcon(QMessageBox.Icon.Warning)
                msg_box.setWindowTitle("Flat Illumination Warning")
                msg_box.setText(
                    "Make sure there is a flat illumination on the detector of somewhere from 5-30 electrons/pixel/sec"
                )
                msg_box.exec()
                self.text_output.append("Starting Bad Pixel Correction...")
                self.text_output.append("Setting output Directory")

                self.client["Autosave Directory"] = self.directory_out
                self.client["Autosave Final Image"] = "On"
                self.client["Exposure Time (seconds)"] = self.acquisition_time
                self.client["Autosave Filename Suffix"] = "BadPixelUnCorrected"
                self.client["Image Processing - Flatfield Correction"] = "None"

                self.client["Image Processing - Bad Pixel Correction"] = (
                    "Off"  # set Bad Pixel Correction Off
                )
                self.text_output.append(
                    f"Starting Acquiring: For {self.acquisition_time} sec"
                )
                self.client.start_acquisition(1)
                self.is_acquiring_raw = True

        else:
            self.start_button.setText("Get Raw")
            self.text_output.append("Stopping Bad Pixel Correction...")
            self.client.stop_acquisition()
            # Add logic for stopping the process here


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Image Processing Tools")

        # Create buttons
        self.bad_pixel_button = QPushButton("Bad Pixel Correction")
        self.magnification_button = QPushButton("Magnification Calibration")

        # Connect buttons to their respective methods
        self.bad_pixel_button.clicked.connect(self.bad_pixel_correction)
        self.magnification_button.clicked.connect(self.magnification_calibration)

        # Set layout
        layout = QHBoxLayout()
        layout.addWidget(self.bad_pixel_button)
        layout.addWidget(self.magnification_button)

        # Set central widget
        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)
        self.bad_pixel_window = None
        self.mag_calibration_window = None

    def bad_pixel_correction(self):
        self.close()
        self.bad_pixel_window = BadPixelCorrectionWindow()

    def magnification_calibration(self):
        print("Magnification Calibration clicked")


if __name__ == "__main__":
    app = QApplication([])
    window = MainWindow()
    window.show()
    app.exec()
