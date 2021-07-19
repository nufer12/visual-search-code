import { Component, OnInit, OnDestroy, ViewChild, ElementRef } from '@angular/core';
import { APIService } from '../api.service';
import { NotificationService } from '../notification.service';
import { GenericList } from '../util/generic-list';

declare var jQuery : any;

@Component({
  selector: 'app-collection-list',
  templateUrl: './collection-list.component.html',
  styleUrls: ['./collection-list.component.scss']
})
export class CollectionListComponent extends GenericList implements OnInit, OnDestroy {

  constructor(public api : APIService, private notifier : NotificationService) {
    super();
  }

  ngOnInit() {
    console.log(this.api.user)
  }

  createNew(title: string, comment: string) {
    document.dispatchEvent(new Event('api-started-loading'));
    this.api.createCollection(title, comment).then(
      data => {
        document.dispatchEvent(new Event('api-finished-loading'));
      }, error => {
        document.dispatchEvent(new Event('api-finished-loading'));
      }
    )
  }

}
