import { Component, OnInit, ViewChild, ElementRef } from '@angular/core';
import { APIService } from '../api.service';
declare var jQuery : any;

@Component({
  selector: 'app-new-collection',
  templateUrl: './new-collection.component.html',
  styleUrls: ['./new-collection.component.css']
})
export class NewCollectionComponent implements OnInit {

  @ViewChild('newCollectionModal') newCollectionModal : ElementRef;

  constructor(public api : APIService) { }

  ngOnInit() {
  }

  createCollection(title: string, comment: string) {
    this.api.createCollection(title, comment).then(
      data => {
        jQuery(this.newCollectionModal.nativeElement).modal('toggle');
      }, error => {
      }
    )
  }
}
