"""Sustituto mínimo de pymongo y bson, SOLO para las pruebas.

Permite probar el servidor sin conectarse a MongoDB: las pruebas nunca tocan tu
base de datos real de Atlas. Implementa únicamente lo que usa este proyecto.
"""
import copy
import itertools
import random
import secrets
import sys
import types


class InvalidId(Exception):
    pass


class PyMongoError(Exception):
    pass


class ObjectId:
    # Como en MongoDB real, cada _id nuevo es mayor que el anterior (sirve para desempatar orden)
    _contador = itertools.count(int(secrets.token_hex(4), 16) << 64)

    def __init__(self, valor=None):
        if valor is None:
            self._hex = "%024x" % next(ObjectId._contador)
        elif isinstance(valor, ObjectId):
            self._hex = valor._hex
        elif isinstance(valor, str) and len(valor) == 24 and all(c in "0123456789abcdefABCDEF" for c in valor):
            self._hex = valor.lower()
        else:
            raise InvalidId("no es un ObjectId válido")

    def __str__(self):
        return self._hex

    def __repr__(self):
        return "ObjectId('%s')" % self._hex

    def __eq__(self, otro):
        return isinstance(otro, ObjectId) and otro._hex == self._hex

    def __hash__(self):
        return hash(self._hex)

    def __lt__(self, otro):
        return self._hex < otro._hex


class _Resultado:
    def __init__(self, **datos):
        self.__dict__.update(datos)


def _coincide(doc, filtro):
    return all(doc.get(clave) == valor for clave, valor in filtro.items())


def _clave_orden(clave):
    # En MongoDB los valores nulos se ordenan antes que cualquier otro
    def f(doc):
        v = doc.get(clave)
        return (v is not None, v if v is not None else 0)

    return f


class _Cursor:
    def __init__(self, docs):
        self._docs = docs

    def sort(self, clave, direccion=1):
        pares = clave if isinstance(clave, list) else [(clave, direccion)]
        for k, d in reversed(pares):
            self._docs.sort(key=_clave_orden(k), reverse=(d == -1))
        return self

    def skip(self, n):
        self._docs = self._docs[n:]
        return self

    def limit(self, n):
        if n:
            self._docs = self._docs[:n]
        return self

    def __iter__(self):
        return iter(copy.deepcopy(self._docs))


class Coleccion:
    def __init__(self):
        self.docs = []

    def create_index(self, *args, **kwargs):
        return "indice"

    def insert_one(self, doc):
        doc.setdefault("_id", ObjectId())
        self.docs.append(copy.deepcopy(doc))
        return _Resultado(inserted_id=doc["_id"])

    def insert_many(self, docs):
        ids = [self.insert_one(d).inserted_id for d in docs]
        return _Resultado(inserted_ids=ids)

    def count_documents(self, filtro):
        return sum(1 for d in self.docs if _coincide(d, filtro))

    def find(self, filtro=None, *args, **kwargs):
        return _Cursor([copy.deepcopy(d) for d in self.docs if _coincide(d, filtro or {})])

    def find_one(self, filtro=None, sort=None):
        cursor = self.find(filtro)
        if sort:
            cursor.sort(sort)
        for doc in cursor:
            return doc
        return None

    def update_one(self, filtro, cambios):
        for doc in self.docs:
            if _coincide(doc, filtro):
                doc.update(copy.deepcopy(cambios.get("$set", {})))
                return _Resultado(matched_count=1, modified_count=1)
        return _Resultado(matched_count=0, modified_count=0)

    def delete_one(self, filtro):
        for i, doc in enumerate(self.docs):
            if _coincide(doc, filtro):
                del self.docs[i]
                return _Resultado(deleted_count=1)
        return _Resultado(deleted_count=0)

    def delete_many(self, filtro):
        antes = len(self.docs)
        self.docs = [d for d in self.docs if not _coincide(d, filtro)]
        return _Resultado(deleted_count=antes - len(self.docs))

    def aggregate(self, etapas):
        docs = [copy.deepcopy(d) for d in self.docs]
        for etapa in etapas:
            if "$match" in etapa:
                docs = [d for d in docs if _coincide(d, etapa["$match"])]
            elif "$sample" in etapa:
                docs = random.sample(docs, min(etapa["$sample"]["size"], len(docs)))
            else:
                raise NotImplementedError(etapa)
        return iter(docs)


class BaseDeDatos:
    def __init__(self):
        self._colecciones = {}

    def __getitem__(self, nombre):
        return self._colecciones.setdefault(nombre, Coleccion())

    def __getattr__(self, nombre):
        if nombre.startswith("_"):
            raise AttributeError(nombre)
        return self[nombre]

    def command(self, nombre):
        return {"ok": 1}


class MongoClient:
    def __init__(self, *args, **kwargs):
        self._bases = {}

    def __getitem__(self, nombre):
        return self._bases.setdefault(nombre, BaseDeDatos())


def instalar():
    """Hace que  import pymongo / import bson  usen este sustituto."""
    pymongo = types.ModuleType("pymongo")
    pymongo.MongoClient = MongoClient
    errores = types.ModuleType("pymongo.errors")
    errores.PyMongoError = PyMongoError
    pymongo.errors = errores

    bson = types.ModuleType("bson")
    bson.ObjectId = ObjectId
    bson_errores = types.ModuleType("bson.errors")
    bson_errores.InvalidId = InvalidId
    bson.errors = bson_errores

    sys.modules.update(
        {
            "pymongo": pymongo,
            "pymongo.errors": errores,
            "bson": bson,
            "bson.errors": bson_errores,
        }
    )
