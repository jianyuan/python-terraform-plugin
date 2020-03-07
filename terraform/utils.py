import datetime
import typing

import msgpack
from cryptography import x509
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec

from terraform.protos import tfplugin5_1_pb2


class CertificatePrivateKey(typing.NamedTuple):
    certificate: x509.Certificate
    private_key: ec.EllipticCurvePrivateKeyWithSerialization


def generate_certificate() -> CertificatePrivateKey:
    key = typing.cast(
        ec.EllipticCurvePrivateKeyWithSerialization,
        ec.generate_private_key(curve=ec.SECP521R1(), backend=default_backend()),
    )

    subject = issuer = x509.Name(
        [
            x509.NameAttribute(
                x509.oid.NameOID.ORGANIZATION_NAME, "python-terraform-plugin"
            ),
            x509.NameAttribute(x509.oid.NameOID.COMMON_NAME, "localhost"),
        ]
    )

    certificate = (
        x509.CertificateBuilder()
        .subject_name(subject)
        .issuer_name(issuer)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(datetime.datetime.utcnow())
        .not_valid_after(datetime.datetime.utcnow() + datetime.timedelta(days=365))
        .add_extension(
            x509.KeyUsage(
                digital_signature=True,
                content_commitment=False,
                key_encipherment=True,
                data_encipherment=False,
                key_agreement=True,
                key_cert_sign=True,
                crl_sign=False,
                encipher_only=False,
                decipher_only=False,
            ),
            critical=True,
        )
        .add_extension(
            x509.ExtendedKeyUsage(
                [
                    x509.oid.ExtendedKeyUsageOID.CLIENT_AUTH,
                    x509.oid.ExtendedKeyUsageOID.SERVER_AUTH,
                ]
            ),
            critical=True,
        )
        .add_extension(x509.BasicConstraints(ca=True, path_length=None), critical=True)
        .add_extension(
            x509.SubjectAlternativeName([x509.DNSName("localhost")]), critical=False,
        )
        .sign(key, hashes.SHA256(), default_backend())
    )

    return CertificatePrivateKey(certificate=certificate, private_key=key)


def encode_certificate_pem(certificate: x509.Certificate) -> bytes:
    return certificate.public_bytes(serialization.Encoding.PEM)


def encode_certificate_der(certificate: x509.Certificate) -> bytes:
    return certificate.public_bytes(serialization.Encoding.DER)


def encode_private_key(key: ec.EllipticCurvePrivateKeyWithSerialization) -> bytes:
    return key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.TraditionalOpenSSL,
        encryption_algorithm=serialization.NoEncryption(),
    )


def to_dynamic_value_proto(value: typing.Any) -> tfplugin5_1_pb2.DynamicValue:
    return tfplugin5_1_pb2.DynamicValue(msgpack=msgpack.packb(value))


def from_dynamic_value_proto(proto: tfplugin5_1_pb2.DynamicValue) -> typing.Any:
    return msgpack.unpackb(proto.msgpack)
