import { Component, OnInit, Input, Output, OnChanges } from '@angular/core';
import { APIGenericDataItem } from '../util/data-types';
import { ManagedSubs } from '../util/managed-subs';
import { ActivatedRoute } from '@angular/router';
import { RemoteDataStructureListSliceable } from '../util/remote-data';
import { APIService } from '../api.service';
import { EventEmitter } from '@angular/core';

@Component({
  selector: 'app-generic-list',
  templateUrl: './generic-list.component.html',
  styleUrls: ['./generic-list.component.scss']
})
export class GenericListComponent extends ManagedSubs implements OnInit, OnChanges {


  @Input() itemType: string;
  @Input() apiArrayKey: string;
  @Input() apiID: number;
  @Input() defaultMessage : string = 'No elements available.'

  public data : APIGenericDataItem[] = [];

  @Input() perPage : number = 20;
  private _page : number = 0;
  @Input()
  get page() : number {
    return this._page;
  }

  @Input() containerClass: string = "row";
  @Input() itemClass: string = "";
  @Input() getParamsKey: string = "page";

  @Input() bootstrapScale : number = -1;

  @Output() newData : EventEmitter<number[]> = new EventEmitter<number[]>();

  private _queryParams;
  public _bootstrapClass : string = "";

  constructor(private route: ActivatedRoute, public api : APIService) {
    super();
  }

  ngOnInit() {
    this.manageSub('getParams', this.route.queryParams.subscribe(queryParams => {
      this._page = (queryParams[this.getParamsKey] != null) ? +queryParams[this.getParamsKey] : 0;
      this._queryParams = queryParams;
      this.loadData();
    }));
    this.setBootstrapClass();
  }

  setBootstrapClass() {
    if(this.bootstrapScale > 0) {
      this._bootstrapClass = 'col-'+this.bootstrapScale;
    } else {
      this._bootstrapClass = this.itemClass;
    }
  }

  loadData() {

    let from = this.page * this.perPage;
    let to = from + this.perPage;

    let requestParams = Object.assign({}, this._queryParams);
    delete requestParams[this.getParamsKey];

    this.manageSub(this.apiArrayKey, (<RemoteDataStructureListSliceable<APIGenericDataItem[]>>this.api.data[this.apiArrayKey]).getSlice(this.apiID, from, to, requestParams).subscribe(
      data => {
        if(data.data) {
          console.log('got new data, wuhuuu')
          this.data = data.data;
          this.newData.emit([data.total, this.perPage]);
        }
        
      })
    );
  }

  ngOnChanges(changes) {
    if(changes['bootstrapScale'] == undefined) {
      this.loadData();
    } else {
      console.log('set bootstrap class')
      this.setBootstrapClass();
    }
  }

}
