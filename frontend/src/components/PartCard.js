import React from "react";
import "./PartCard.css";

function PartCard({ metadata }) {
  if (!metadata || metadata.type !== "part") return null;
  return (
    <div className="part-card">
      <div className="part-card__top">
        {metadata.image_url && (
          <img src={metadata.image_url} alt={metadata.part_name} className="part-card__image" />
        )}
        <div className="part-card__info">
          <div className="part-card__name">{metadata.part_name}</div>
          <div className="part-card__number">Part #{metadata.part_number}</div>
          <div className="part-card__row">
            <span className="part-card__price">${metadata.price}</span>
            <span className={`part-card__availability ${metadata.availability === 'In Stock' ? 'in-stock' : 'out-of-stock'}`}>
              {metadata.availability === 'In Stock' ? '✓ In Stock' : '✗ Out of Stock'}
            </span>
          </div>
          <a href={metadata.product_url} target="_blank" rel="noreferrer" className="part-card__buy">
            Buy on PartSelect
          </a>
        </div>
      </div>
      {metadata.video_thumbnail_url && (
        <a href={metadata.video_url} target="_blank" rel="noreferrer" className="part-card__video">
          <img src={metadata.video_thumbnail_url} alt="Repair video" className="part-card__video-thumb" />
          <span className="part-card__video-label">▶ Watch Repair Video</span>
        </a>
      )}
    </div>
  );
}

export default PartCard;
