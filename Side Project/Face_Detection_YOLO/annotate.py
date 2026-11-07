import cv2
from pathlib import Path

# Lokasi dataset
base_folder = Path(__file__).resolve().parent / "Face_Detection_YOLO"
image_folder = base_folder / r"D:\Python\Project_AI\Face_Detection_YOLO\dataset\images\train"
label_folder = base_folder / r"D:\Python\Project_AI\Face_Detection_YOLO\dataset\labels\train"

label_folder.mkdir(parents=True, exist_ok=True)

images = sorted(image_folder.glob("*.jpg"))

if not images:
    raise FileNotFoundError("Tidak ada gambar!")

# Variabel anotasi
start_point = None
end_point = None
drawing = False
boxes = []

def draw_box(event, x, y, flags, param):
    global start_point, end_point, drawing

    if event == cv2.EVENT_LBUTTONDOWN:
        start_point = (x, y)
        end_point = (x, y)
        drawing = True

    elif event == cv2.EVENT_MOUSEMOVE:
        if drawing:
            end_point = (x, y)

    elif event == cv2.EVENT_LBUTTONUP:
        end_point = (x, y)
        drawing = False

        x1, y1 = start_point
        x2, y2 = end_point

        # Memastikan koordinat terurut
        x1, x2 = sorted([x1, x2])
        y1, y2 = sorted([y1, y2])

        boxes.append((x1, y1, x2, y2))


# Memproses setiap gambar
for image_path in images:

    image = cv2.imread(str(image_path))

    if image is None:
        print(f"Gagal membaca: {image_path.name}")
        continue

    height, width = image.shape[:2]
    boxes = []

    cv2.namedWindow("Face Annotation")
    cv2.setMouseCallback("Face Annotation", draw_box)

    while True:
        display = image.copy()

        # Menggambar kotak yang sudah selesai
        for x1, y1, x2, y2 in boxes:
            cv2.rectangle(display, (x1, y1), (x2, y2), (0, 255, 0), 2)

        # Menggambar kotak saat mouse masih ditahan
        if drawing and start_point and end_point:
            cv2.rectangle(
                display, start_point, end_point, (0, 255, 0), 2
            )

        cv2.imshow("Face Annotation", display)

        key = cv2.waitKey(1) & 0xFF

        # Simpan anotasi
        if key == ord("s"):

            label_path = label_folder / f"{image_path.stem}.txt"

            with open(label_path, "w") as file:
                for x1, y1, x2, y2 in boxes:

                    x_center = ((x1 + x2) / 2) / width
                    y_center = ((y1 + y2) / 2) / height
                    box_width = (x2 - x1) / width
                    box_height = (y2 - y1) / height

                    file.write(
                        f"0 {x_center} {y_center} "
                        f"{box_width} {box_height}\n"
                    )

            print(f"Anotasi disimpan: {label_path.name}")

        # Foto berikutnya
        elif key == ord("n"):
            break

        # Keluar
        elif key == ord("q"):
            cv2.destroyAllWindows()
            raise SystemExit

    cv2.destroyAllWindows()

print("Semua foto selesai diproses!")