from os import urandom
from hashlib import sha256
from hmac import compare_digest
import pickle
import os
from zlib import compress, decompress, crc32


class Usuario:
    def __init__(self, nombre_usuario="", password_no_encriptada="", lista_amigos=None):
        self.nombre_usuario = nombre_usuario
        if lista_amigos is None:
            self.lista_amigos = []
        else:
            self.lista_amigos = lista_amigos

        self.sal = urandom(5)
        self.password = self.encriptar_password(password_no_encriptada).hexdigest()

    def encriptar_password(self, password_no_encriptada):
        return sha256(self.sal + password_no_encriptada.encode("utf-8"))

    def verificar_password(self, pass_a_verificar):
        secuencia_encriptada = sha256(self.sal + pass_a_verificar.encode("utf-8"))
        return compare_digest(secuencia_encriptada.hexdigest(), self.password)

    @staticmethod
    def existe_usuario(user_name):
        return "{}.user".format(user_name) in os.listdir("database/usuarios")

    @staticmethod
    def crear_usuario(user_name, passw):
        usuario = Usuario(user_name, passw)
        with open("database/usuarios/{}.user".format(user_name), "wb") as file:
            pickle.dump(obj=usuario, file=file)

    @staticmethod
    def cargar_usuario(user_name):
        with open("database/usuarios/{}.user".format(user_name), "rb") as file:
            return pickle.load(file)


class Image:
    @staticmethod
    def get_data(filename):
        signature = None
        ihdr = {}
        idat = bytearray()
        iend = None

        with open(filename, "rb") as file:
            signature = file.read(8)
            while True:
                largo_info = int.from_bytes(file.read(4), byteorder="big")
                tipo_chunk = file.read(4).decode()
                if tipo_chunk == "IHDR":
                    ihdr["ancho"] = int.from_bytes(file.read(4), byteorder="big")
                    ihdr["alto"] = int.from_bytes(file.read(4), byteorder="big")
                    ihdr["profundidad"] = int.from_bytes(file.read(1), byteorder="big")
                    ihdr["tipo_de_colores"] = int.from_bytes(file.read(1), byteorder="big")
                    ihdr["tipo_de_compresion"] = int.from_bytes(file.read(1), byteorder="big")
                    ihdr["tipo_de_filtro"] = int.from_bytes(file.read(1), byteorder="big")
                    ihdr["tipo_de_entrelazado"] = int.from_bytes(file.read(1), byteorder="big")
                    file.read(4)
                elif tipo_chunk == "IDAT":
                    info_idat = file.read(largo_info)
                    idat.extend(info_idat)
                    file.read(4)
                elif tipo_chunk == "IEND":
                    iend = file.read()
                    break
                else:
                    file.read(largo_info + 4)

        return signature, ihdr, decompress(idat), iend

    @staticmethod
    def bytes2matrix(ihdr, idat):
        matriz = []
        data = iter(idat)
        num_of_elements = (1 + ihdr["ancho"]) * ihdr["alto"]
        for element in range(num_of_elements):
            if element % (ihdr["ancho"] + 1) == 0:
                matriz.append([next(data)])
            else:
                r = next(data)
                g = next(data)
                b = next(data)
                matriz[element // (ihdr["ancho"] + 1)].append(tuple((r, g, b)))
        return matriz

    @staticmethod
    def matrix2string(matriz):
        """
        Este método transforma la matriz en un string de bytes.
        """
        out = b''
        for i in range(len(matriz)):
            out += (0).to_bytes(1, byteorder='big')
            for j in range(1, len(matriz[i])):
                for k in matriz[i][j]:
                    out += k.to_bytes(1, byteorder='big')
        return out

    @staticmethod
    def grey(ihdr, matriz):
        salida = []
        ihdr.update({"tipo_de_colores": 0})
        for fila in matriz:
            nueva_fila = []
            for i, elemento in enumerate(fila):
                if i == 0:
                    nueva_fila.append(elemento)
                else:
                    nueva_fila.append(tuple([int(sum(elemento)/len(elemento))]))
            salida.append(nueva_fila)

        return ihdr, salida

    @staticmethod
    def sepia(ihdr, matriz):
        salida = []
        ihdr.update({"tipo_de_colores": 2})
        for fila in matriz:
            nueva_fila = []
            for i, elemento in enumerate(fila):
                if i == 0:
                    nueva_fila.append(elemento)
                else:
                    R = min(int(elemento[0] * .393 + elemento[1] * .769 + elemento[2] * .189), 255)
                    G = min(int(elemento[0] * .349 + elemento[1] * .686 + elemento[2] * .168), 255)
                    B = min(int(elemento[0] * .272 + elemento[1] * .534 + elemento[2] * .131), 255)
                    nueva_fila.append(tuple([R, G, B]))
            salida.append(nueva_fila)

        return ihdr, salida

    @staticmethod
    def set_data(signature, ihdr, idat):
        idat = compress(idat, 9)
        new_image = bytearray()
        new_image.extend(signature)

        new_ihdr_data = bytearray()
        ihdr_data_length = [("ancho", 4), ("alto", 4), ("profundidad", 1), ("tipo_de_colores", 1),
                            ("tipo_de_compresion", 1), ("tipo_de_filtro", 1), ("tipo_de_entrelazado", 1)]
        for dato, largo in ihdr_data_length:
            new_ihdr_data.extend(ihdr[dato].to_bytes(length=largo, byteorder="big"))

        new_image.extend(len(new_ihdr_data).to_bytes(length=4, byteorder="big"))
        new_image.extend("IHDR".encode())
        new_image.extend(new_ihdr_data)
        new_image.extend(int.to_bytes(crc32("IHDR".encode() + bytes(new_ihdr_data)), length=4, byteorder="big"))

        new_image.extend(len(idat).to_bytes(length=4, byteorder="big"))
        new_image.extend("IDAT".encode())
        new_image.extend(idat)
        new_image.extend(crc32("IDAT".encode() + idat).to_bytes(length=4, byteorder="big"))

        new_image.extend(bytes(4))
        new_image.extend("IEND".encode())
        new_image.extend(crc32("IEND".encode()).to_bytes(length=4, byteorder="big"))

        return new_image

    @staticmethod
    def get_grey(filename):
        firma, ihdr, data, end = Image.get_data(filename)
        matriz = Image.bytes2matrix(ihdr, data)
        ihdr_gris, matriz_gris = Image.grey(ihdr, matriz)
        idat_gris = Image.matrix2string(matriz_gris)
        return Image.set_data(firma, ihdr_gris, idat_gris)

    @staticmethod
    def get_sepia(filename):
        firma, ihdr, data, end = Image.get_data(filename)
        matriz = Image.bytes2matrix(ihdr, data)
        ihdr_sepia, matriz_sepia = Image.sepia(ihdr, matriz)
        idat_sepia = Image.matrix2string(matriz_sepia)
        return Image.set_data(firma, ihdr_sepia, idat_sepia)


if __name__ == "__main__":
    Usuario.crear_usuario("test", "test")
    print(Usuario.existe_usuario("test"))
    user = Usuario.cargar_usuario("test")
    print(user.verificar_password("hola"))
    print(user.verificar_password("test"))

