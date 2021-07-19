import { Component, OnInit, ViewChild, ElementRef, Input, Output } from '@angular/core';
import { APIService } from '../api.service';
import { GenericListItem } from '../util/generic-list';
import { ActivatedRoute } from '@angular/router';
import { SearchResult } from '../util/data-types';
import { FavoriteService } from '../favorite.service';

@Component({
  selector: 'app-favorites-item',
  templateUrl: './favorites-item.component.html',
  styleUrls: ['./favorites-item.component.scss']
})
export class FavoritesItemComponent extends GenericListItem<number> implements OnInit {

  public result : SearchResult;
  public searchID: number;
  public collectionID: number;


  public isFavorite : boolean = true;

  @ViewChild('mainContainer') mainContainer : ElementRef;

  constructor(public favs: FavoriteService, public api: APIService, private route : ActivatedRoute) {
    super();
  }

  ngOnInit() {
    this.manageSub('path', this.route.params.subscribe(params => {
      this.collectionID = +params['id'];
      this.searchID = +params['searchid'];
      this.api.data["searchResults"].get(this.searchID).subscribe(
        data => {
          if(data) {
            this.result = (<SearchResult[]>data.data).filter(el => {
              return el.id == this.item;
            })[0];
          }
        }
      )
    }));
  }

  ondragstart(ev) {
    ev.dataTransfer.setData("text", ''+this.item);
    this.favs.isDragging = true;
  }
  ondragend(ev) {
    this.favs.isDragging = false;
  }
  ondragenter(ev) {
    console.log('drag is over');
    ev.target.classList.add('drag-is-over');
  }
  ondragleave(ev) {
    ev.target.classList.remove('drag-is-over');
  }
  ondrop(ev) {
    let dropped = +ev.dataTransfer.getData("text");
    let dropTarget = this.item;
    
    this.favs.reorder(this.searchID, <number>dropTarget, dropped);

    ev.target.classList.remove('drag-is-over');
    this.favs.isDragging = false;
    ev.preventDefault();
    return false;
  }

  allowDrop(ev) {
    ev.preventDefault();
  }
}
