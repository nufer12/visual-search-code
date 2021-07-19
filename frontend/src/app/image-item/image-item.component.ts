import { Component, OnInit, OnDestroy } from '@angular/core';
import { APIService } from '../api.service';
import { GenericListItem } from '../util/generic-list';
import { ActivatedRoute } from '@angular/router';
import { ImageData } from '../util/data-types';

@Component({
  selector: 'app-image-item',
  templateUrl: './image-item.component.html',
  styleUrls: ['./image-item.component.scss']
})
export class ImageItemComponent extends GenericListItem<ImageData> implements OnInit, OnDestroy {

  public collectionID : number;

  constructor(public api: APIService, private route: ActivatedRoute) {
    super();
  }

  ngOnInit() {
    this.manageSub('path', this.route.params.subscribe(params => {
      this.collectionID = +params['id'];
    }));
  }

}
