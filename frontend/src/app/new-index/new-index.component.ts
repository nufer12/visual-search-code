import { Component, OnInit, ViewChild, ElementRef } from '@angular/core';
import { APIService } from '../api.service';
import { IndexType, Collection, Worker } from '../util/data-types';
import { ManagedSubs } from '../util/managed-subs';
import { ActivatedRoute } from '@angular/router';

declare var jQuery : any;

@Component({
  selector: 'app-new-index',
  templateUrl: './new-index.component.html',
  styleUrls: ['./new-index.component.css']
})
export class NewIndexComponent extends ManagedSubs implements OnInit {

  public indexTypes : IndexType[] = null;
  public collectionID : number;

  private _indexType : number = -1;
  get indexType() : number {
    return this._indexType;
  }
  set indexType(type : number) {

    if(this.indexTypes == null) {
      return;
    }

    this._indexType = type;
    let index = this.indexTypes.filter(el => {
      return el.id == type;
    });
    if(index.length > 0) {
      this.indexDescription = index[0].description;
    } else {
      this.indexDescription = "";
    }
  }

  public indexMachine : number = -1;


  public indexName : string = "";
  public indexDescription : string = "";
  public workers : Worker[];

  @ViewChild('indexModal') indexModal : ElementRef;

  constructor(public api : APIService, private route : ActivatedRoute) {
    super();
  }

  ngOnInit() {
    this.manageSub('path', this.route.params.subscribe(params => {
      this.collectionID = +params['id'];
      this.manageSub('indextypes', this.api.data['indexTypes'].get(this.collectionID).subscribe(
        data => {
          if(data) {
            this.indexTypes = data.data
          }
        }
      ));
      this.manageSub("workers", this.api.getWorkers().subscribe(workers => {
        this.workers = workers.filter(worker => {
          return worker.type == 0;
        });
      }));
    }));
  }


  createIndex() {
    this.api.createIndex(this.collectionID, this.indexName, this.indexType, this.indexMachine).then(data => {
      jQuery(this.indexModal.nativeElement).modal('toggle');
    }, errorMsg => {
    })
  }

}
