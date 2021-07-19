import { Component, OnInit, Input, OnChanges } from '@angular/core';
import { ManagedSubs } from '../util/managed-subs';
import { ActivatedRoute } from '@angular/router';

@Component({
  selector: 'app-generic-list-pagination',
  templateUrl: './generic-list-pagination.component.html',
  styleUrls: ['./generic-list-pagination.component.css']
})
export class GenericListPaginationComponent extends ManagedSubs implements OnInit, OnChanges {
  
  private _total: number = 0;
  @Input()
  get total() : number {
    return this._total;
  }
  set total(n: number) {
    this._total = n;
    this.calcPageNumbers();
  }
  private _page : number = 0;
  @Input() perPage : number = 20;
  @Input() getParamsKey: string = "page"
  private _queryParams = {};
  public lastPage = 0;

  
  public paginationList : number[] = [];
  calcPageNumbers() {
    let maxPages = Math.ceil(this._total / this.perPage);
    this.paginationList = [this._page - 3, this._page - 2, this._page - 1, this._page, this._page + 1, this._page + 2, this._page + 3].filter(el => {
      return el >= 0 && el < maxPages;
    });
    this.lastPage = this.paginationList[this.paginationList.length - 1];
  }

  constructor(private route: ActivatedRoute) {
    super();
  }

  ngOnInit() {
    this.manageSub('getParams', this.route.queryParams.subscribe(queryParams => {
      this._page = (queryParams[this.getParamsKey] != null) ? +queryParams[this.getParamsKey] : 0;
      this._queryParams = queryParams;
      this.calcPageNumbers();
    }));
  }

  getQueryParam(i) {
    
    let params = Object.assign({}, this._queryParams);
    params[this.getParamsKey] = i;

    return params;
  }

  ngOnChanges() {

    this.calcPageNumbers();

  }
}
