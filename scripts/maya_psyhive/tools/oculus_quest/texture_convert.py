import subprocess
import os
import time

CREATE_NO_WINDOW = 0x08000000

def run_process(cmd):
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, creationflags=CREATE_NO_WINDOW)
    (stdout, stderr) = p.communicate()
    print "############################"
    print " ".join(cmd)
    print "############################"
    print stdout
    return stdout, stderr


def get_image_dimensions(image):
    cmd = ["C:/Program Files/ImageMagick-7.0.8-Q16/magick.exe", "identify", "-format", "%wx%h", image]
    (stdout, stderr) = run_process(cmd)
    width, height = stdout.split("x")
    return width, height


def convert_to_linear_exr(input_texture, output_exr):
    # Convert to linear exr
    cmd = [
        "//coppi/glob/bin/Arnold/MtoA-3.2.0.2-win64-2018/bin/maketx.exe",
        "-resize",
        "-nomipmap",
        "--colorconvert", "sRGB", "linear",
        "-d", "half",
        "-o", output_exr,
        input_texture
    ]
    run_process(cmd)
    if not os.path.exists(output_exr):
        raise Exception("Cannot find EXR, '{}'".format(output_exr))


def generate_temp_name(input_name, extension):
    output_name = os.path.splitext(input_name)[0]
    output_name += "_temp_"
    output_name += str(time.time())
    output_name += "." + extension
    return output_name


def create_resized_image(input_texture, output_texture, x_res, y_res):
    cmd = [
        "C:/Program Files/ImageMagick-7.0.8-Q16/magick.exe", "convert",
        "-resize", "{}x{}".format(x_res, y_res),
        "-alpha", "off",
        "-compress", "zip",
        "-colorspace", "sRGB",
        input_texture,
        output_texture
    ]
    run_process(cmd)


def create_combined_mipmap(full_res_image, output_texture, mip_image_list=[]):
    # Create combined mipmap
    cmd = [
        "//coppi/glob/bin/Arnold/MtoA-3.2.0.2-win64-2018/bin/maketx.exe",
        full_res_image,
        "-d", "uint8",
        "-o", output_texture
    ]
    for mip_image in mip_image_list:
        cmd.append("-mipimage")
        cmd.append(mip_image)
    run_process(cmd)


def mipmap_texture_scalar(input_texture, output_texture):
    create_combined_mipmap(input_texture, output_texture)


def mipmap_texture_colorsafe(input_texture, output_texture):
    input_texture = input_texture.replace("\\", "/")
    output_texture = output_texture.replace("\\", "/")

    temp_exr = generate_temp_name(output_texture, "exr")
    convert_to_linear_exr(input_texture, temp_exr)
    x, y = get_image_dimensions(temp_exr)
    x = int(x)
    y = int(y)

    resolutions = []
    while 1:
        resolutions.append([x,y])
        if x == 1 and y == 1:
            break
        x = max(1, x / 2)
        y = max(1, y / 2)

    mip_images = []
    for x, y in resolutions:
        temp_mip_image = "{}_{}x{}.exr".format(os.path.splitext(temp_exr)[0], str(x), str(y))
        create_resized_image(temp_exr, temp_mip_image, x, y)
        mip_images.append(temp_mip_image)

    create_combined_mipmap(mip_images[0], output_texture, mip_images[1:])

    for image in mip_images + [temp_exr]:
        if os.path.exists(image):
            os.remove(image)


def mipmap_texture(input_texture, output_texture, colorspace):
    print "{} colorspace: {} -> {}".format(colorspace, input_texture, output_texture)
    #if colorspace in ["linear", "Raw"]:
    if colorspace in ["linear", "raw"]:
        mipmap_texture_scalar(input_texture, output_texture)
    elif colorspace == "sRGB":
        mipmap_texture_colorsafe(input_texture, output_texture)
    else:
        raise Exception("Colorspace '{}' not recognized for texture '{}'".format(colorspace, input_texture))
