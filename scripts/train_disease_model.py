from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description="Train a CNN disease model (Keras) from an image folder dataset.")
    parser.add_argument("--data_dir", required=True, help="Dataset directory with subfolders per class label")
    parser.add_argument("--out", default="models/disease_model.keras", help="Output .keras model path")
    args = parser.parse_args()

    try:
        import tensorflow as tf  # type: ignore
    except Exception as exc:
        raise SystemExit(
            "TensorFlow is not installed. Install appropriate TensorFlow packages for your machine to train the CNN."
        ) from exc

    data_dir = Path(args.data_dir)
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    img_size = (224, 224)
    batch_size = 32

    train_ds = tf.keras.utils.image_dataset_from_directory(
        data_dir,
        validation_split=0.2,
        subset="training",
        seed=42,
        image_size=img_size,
        batch_size=batch_size,
    )
    val_ds = tf.keras.utils.image_dataset_from_directory(
        data_dir,
        validation_split=0.2,
        subset="validation",
        seed=42,
        image_size=img_size,
        batch_size=batch_size,
    )

    class_names = list(train_ds.class_names)
    (out_path.with_suffix(".labels.json")).write_text(json.dumps(class_names, indent=2), encoding="utf-8")
    print("Labels:", class_names)

    normalization = tf.keras.layers.Rescaling(1.0 / 255)
    base = tf.keras.applications.MobileNetV2(
        input_shape=img_size + (3,),
        include_top=False,
        weights="imagenet",
    )
    base.trainable = False

    inputs = tf.keras.Input(shape=img_size + (3,))
    x = normalization(inputs)
    x = base(x, training=False)
    x = tf.keras.layers.GlobalAveragePooling2D()(x)
    x = tf.keras.layers.Dropout(0.2)(x)
    outputs = tf.keras.layers.Dense(len(class_names), activation="softmax")(x)
    model = tf.keras.Model(inputs, outputs)

    model.compile(optimizer="adam", loss="sparse_categorical_crossentropy", metrics=["accuracy"])
    model.fit(train_ds, validation_data=val_ds, epochs=6)

    model.save(out_path)
    print(f"Saved model: {out_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
